"""
Incremental Synchronization and Deletion Services (§8.10, §11.16).

IncrementalSyncService diffs file content_hashes across commits, re-parsing,
re-chunking, and re-embedding only changed or added files while leveraging
EmbeddingCache. Rebuilds BM25 index and switches commit_sha atomically.

RepoDeletionService purges all MongoDB collections, vector stores, BM25 indices,
and filesystem snapshots for a deleted repository.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.mongo import get_collection
from app.db.redis import get_redis_client
from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.symbols import SymbolRepository
from app.services.chunking.chunker import CodeChunker
from app.services.indexing.embeddings.cache import EmbeddingCache
from app.services.indexing.embeddings.factory import get_embedding_provider
from app.services.indexing.vector.factory import get_vector_store
from app.services.ingestion.archive import SafeArchiveExtractor
from app.services.ingestion.filter import IngestionFilter
from app.services.ingestion.github_fetcher import GitHubFetcher
from app.services.keyword.bm25_index import BM25Index, get_bm25_manager
from app.services.parsing.registry import ParsedFile, ParserRegistry
from app.services.redaction.redactor import SecretRedactor

logger = logging.getLogger(__name__)


class RepoDeletionService:
    """Purges all persistent artifacts for a repository across Mongo, vectors, and disk (§11.16)."""

    def __init__(
        self,
        repo_repo: RepositoryRepository | None = None,
        file_repo: FileRepository | None = None,
        symbol_repo: SymbolRepository | None = None,
        chunk_repo: ChunkRepository | None = None,
    ) -> None:
        self.repo_repo = repo_repo or RepositoryRepository()
        self.file_repo = file_repo or FileRepository()
        self.symbol_repo = symbol_repo or SymbolRepository()
        self.chunk_repo = chunk_repo or ChunkRepository()
        self.settings = get_settings()

    async def delete_repository_data(self, repo_id: str) -> None:
        """Completely purges all data belonging to repo_id."""
        logger.info("Purging repository data for repo_id=%s", repo_id)

        # 1. Mongo documents
        await self.chunk_repo.delete_for_repo(repo_id)
        await self.symbol_repo.delete_for_repo(repo_id)
        await self.file_repo.delete_for_repo(repo_id)
        await self.repo_repo.delete_repository(repo_id)

        # Delete jobs, overviews, and other auxiliary collections
        for col_name in ["jobs", "repo_overviews", "graph_edges", "reviews"]:
            try:
                col = get_collection(col_name)
                await col.delete_many({"repo_id": repo_id})
            except Exception as e:
                logger.warning("Error deleting %s for repo %s: %s", col_name, repo_id, e)

        # 2. Vector store collections
        try:
            vector_store = get_vector_store(
                store_type=self.settings.VECTOR_STORE,
                repo_id=repo_id,
                model_slug=self.settings.EMBEDDING_MODEL,
            )
            vector_store.drop()
        except Exception as e:
            logger.warning("Error dropping vector store for %s: %s", repo_id, e)

        # 3. BM25 indexes
        try:
            get_bm25_manager().delete_index(repo_id)
        except Exception as e:
            logger.warning("Error purging BM25 indexes for %s: %s", repo_id, e)

        # 4. Filesystem artifacts: snapshots, indexes, and uploads
        snapshots_dir = Path(self.settings.DATA_DIR) / "snapshots" / repo_id
        if snapshots_dir.exists():
            shutil.rmtree(snapshots_dir, ignore_errors=True)

        indexes_dir = Path(self.settings.DATA_DIR) / "indexes" / repo_id
        if indexes_dir.exists():
            shutil.rmtree(indexes_dir, ignore_errors=True)

        # 5. Clean Redis keys / locks
        try:
            redis = get_redis_client()
            await redis.delete(f"lock:repo:{repo_id}")
        except Exception:
            pass

        logger.info("Successfully purged all repository data for repo_id=%s", repo_id)


class IncrementalSyncService:
    """
    Performs incremental repository synchronization (§8.10).
    Diffs file content_hashes against the new snapshot, re-parsing and re-embedding
    only added/changed files, removing stale vectors/symbols/chunks, and updating BM25.
    """

    def __init__(
        self,
        repo_repo: RepositoryRepository | None = None,
        file_repo: FileRepository | None = None,
        symbol_repo: SymbolRepository | None = None,
        chunk_repo: ChunkRepository | None = None,
    ) -> None:
        self.repo_repo = repo_repo or RepositoryRepository()
        self.file_repo = file_repo or FileRepository()
        self.symbol_repo = symbol_repo or SymbolRepository()
        self.chunk_repo = chunk_repo or ChunkRepository()
        self.settings = get_settings()

    async def sync_repository(
        self,
        repo_id: str,
        new_ref: str | None = None,
        archive_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Synchronizes repository with a new commit ref or archive.
        Returns summary of changes: status, commit_sha, added, changed, removed file counts.
        """
        repo = await self.repo_repo.get_by_id(repo_id)
        if not repo:
            raise AppError(f"Repository {repo_id} not found", code="REPO_NOT_FOUND")

        old_commit_sha = repo.get("commit_sha")
        source = repo.get("source", {})
        source_type = source.get("type", "github")
        temp_archive_path: str | None = archive_path
        new_commit_sha: str = ""

        # 1. Fetch / determine new commit SHA
        if source_type == "github":
            owner = source.get("owner", "")
            repo_name = source.get("repo", "")
            target_ref = new_ref or source.get("ref", "HEAD")
            fetcher = GitHubFetcher()

            new_commit_sha = await fetcher.resolve_commit_sha(owner, repo_name, target_ref)
            if old_commit_sha and new_commit_sha == old_commit_sha:
                return {
                    "status": "unchanged",
                    "commit_sha": new_commit_sha,
                    "message": "Repository is already up to date.",
                    "added_files": 0,
                    "changed_files": 0,
                    "removed_files": 0,
                }

            # Download new archive
            tarball_dir = Path(self.settings.DATA_DIR) / "uploads" / "tmp"
            tarball_dir.mkdir(parents=True, exist_ok=True)
            temp_archive_path = str(tarball_dir / f"{repo_id}_{new_commit_sha}.tar.gz")
            await fetcher.download_tarball(owner, repo_name, new_commit_sha, temp_archive_path)

        elif source_type == "upload":
            if not temp_archive_path or not Path(temp_archive_path).exists():
                raise AppError("Archive path not found for sync", code="FILE_NOT_FOUND")
            import hashlib

            with open(temp_archive_path, "rb") as f_arch:
                f_hash = hashlib.sha256(f_arch.read(65536)).hexdigest()[:16]
            new_commit_sha = f"upload_{f_hash}"
            if old_commit_sha and new_commit_sha == old_commit_sha:
                return {
                    "status": "unchanged",
                    "commit_sha": new_commit_sha,
                    "message": "Archive content is identical to current snapshot.",
                    "added_files": 0,
                    "changed_files": 0,
                    "removed_files": 0,
                }
        else:
            new_commit_sha = new_ref or "sync_snapshot"

        # 2. Extract new snapshot
        new_snapshot_dir = Path(self.settings.DATA_DIR) / "snapshots" / repo_id / new_commit_sha
        extractor = SafeArchiveExtractor()
        if temp_archive_path:
            if temp_archive_path.endswith((".tar.gz", ".tar")) or source_type == "github":
                extractor.extract_tar(temp_archive_path, str(new_snapshot_dir), strip_root_dir=True)
            else:
                extractor.extract_zip(
                    temp_archive_path, str(new_snapshot_dir), strip_root_dir=False
                )

        # 3. Filter files in new snapshot
        extra_ignores = repo.get("settings", {}).get("extra_ignore_patterns", [])
        file_filter = IngestionFilter(str(new_snapshot_dir), extra_ignore_patterns=extra_ignores)
        new_valid_files, new_skipped_files = file_filter.scan_and_filter()

        # 4. Diff against existing files in MongoDB
        old_files = await self.file_repo.list_files(repo_id, limit=20000)
        old_files_by_path = {f["path"]: f for f in old_files}
        new_files_by_path = {f["path"]: f for f in new_valid_files}

        added_paths = set(new_files_by_path.keys()) - set(old_files_by_path.keys())
        removed_paths = set(old_files_by_path.keys()) - set(new_files_by_path.keys())
        changed_paths = {
            p
            for p in (set(old_files_by_path.keys()) & set(new_files_by_path.keys()))
            if old_files_by_path[p].get("content_hash") != new_files_by_path[p].get("content_hash")
        }

        logger.info(
            "Sync diff for repo %s: %d added, %d changed, %d removed",
            repo_id,
            len(added_paths),
            len(changed_paths),
            len(removed_paths),
        )

        # Setup embedding provider and vector store
        embed_cfg = repo.get("embedding", {})
        provider_name = embed_cfg.get("provider", self.settings.EMBEDDING_PROVIDER)
        model_name = embed_cfg.get("model", self.settings.EMBEDDING_MODEL)
        provider = get_embedding_provider(provider_name, model=model_name)
        vector_store = get_vector_store(
            store_type=self.settings.VECTOR_STORE,
            repo_id=repo_id,
            model_slug=provider.model,
        )
        cache = EmbeddingCache()

        # 5. Delete stale symbols, chunks, files, and vectors for removed or changed files
        paths_to_delete = list(removed_paths | changed_paths)
        if paths_to_delete:
            old_chunks = await self.chunk_repo.get_chunks_for_files(repo_id, paths_to_delete)
            old_chunk_ids = [str(c["_id"]) for c in old_chunks]
            if old_chunk_ids:
                vector_store.delete(old_chunk_ids)
            await self.chunk_repo.delete_by_files(repo_id, paths_to_delete)
            await self.symbol_repo.delete_by_files(repo_id, paths_to_delete)

        if removed_paths:
            await self.file_repo.delete_by_paths(repo_id, list(removed_paths))

        # 6. Parse, redact, and chunk added and changed files
        paths_to_process = list(added_paths | changed_paths)
        parser_registry = ParserRegistry()
        redactor = SecretRedactor()
        chunker = CodeChunker()

        new_symbols_to_upsert: list[dict[str, Any]] = []
        new_chunks_to_upsert: list[dict[str, Any]] = []
        updated_files_to_upsert: list[dict[str, Any]] = []
        parsed_files_for_summaries: list[ParsedFile] = []

        for p in paths_to_process:
            file_doc = new_files_by_path[p]
            file_doc["commit_sha"] = new_commit_sha
            disk_path = new_snapshot_dir / p
            try:
                with open(disk_path, encoding="utf-8", errors="replace") as f_src:
                    source_code = f_src.read()
            except Exception:
                source_code = ""

            parsed = parser_registry.parse_file(source_code, p, file_doc.get("language"))
            parsed_files_for_summaries.append(parsed)
            file_doc["symbols_count"] = len(parsed.symbols)
            file_doc["imports"] = parsed.imports
            file_doc["card"] = parsed.card
            file_doc["is_entry_point"] = len(parsed.entry_point_hints) > 0

            for s in parsed.symbols:
                new_symbols_to_upsert.append(s.to_dict(repo_id=repo_id, path=p))

            redact_res = redactor.redact(source_code)
            file_doc["redaction_count"] = redact_res.redaction_count

            file_chunks = chunker.chunk_file(
                parsed_file=parsed,
                redacted_source=redact_res.redacted_text,
                repo_id=repo_id,
                commit_sha=new_commit_sha,
            )
            new_chunks_to_upsert.extend(file_chunks)
            updated_files_to_upsert.append(file_doc)

        if updated_files_to_upsert:
            await self.file_repo.upsert_files(repo_id, updated_files_to_upsert)
        if new_symbols_to_upsert:
            await self.symbol_repo.bulk_upsert_symbols(repo_id, new_symbols_to_upsert)
        if new_chunks_to_upsert:
            await self.chunk_repo.bulk_upsert_chunks(repo_id, new_chunks_to_upsert)

        # 7. Incremental embedding: check cache for each chunk before embedding
        if new_chunks_to_upsert:
            content_hashes = [c["content_hash"] for c in new_chunks_to_upsert]
            cached_vectors = await cache.get_cached_embeddings(provider.model, content_hashes)

            vectors_to_upsert: list[list[float]] = []
            ids_to_upsert: list[str] = []
            metas_to_upsert: list[dict[str, Any]] = []

            texts_to_embed: list[str] = []
            chunks_to_embed_indices: list[int] = []

            for i, chunk in enumerate(new_chunks_to_upsert):
                c_id = str(chunk.get("_id") or chunk.get("chunk_id"))
                ch = chunk["content_hash"]
                meta = {
                    "path": chunk.get("path", ""),
                    "chunk_type": chunk.get("chunk_type", ""),
                    "start_line": chunk.get("start_line", 1),
                    "end_line": chunk.get("end_line", 1),
                }

                if ch in cached_vectors:
                    # Cache hit!
                    ids_to_upsert.append(c_id)
                    vectors_to_upsert.append(cached_vectors[ch])
                    metas_to_upsert.append(meta)
                else:
                    # Cache miss: queue for embedding
                    texts_to_embed.append(chunk.get("embed_text") or chunk.get("text", ""))
                    chunks_to_embed_indices.append(i)

            # Compute embeddings for cache misses
            if texts_to_embed:
                computed_vectors = provider.embed_documents(texts_to_embed)
                items_to_cache: list[tuple[str, list[float]]] = []
                for idx, vec in zip(chunks_to_embed_indices, computed_vectors, strict=False):
                    chunk = new_chunks_to_upsert[idx]
                    c_id = str(chunk.get("_id") or chunk.get("chunk_id"))
                    ch = chunk["content_hash"]
                    meta = {
                        "path": chunk.get("path", ""),
                        "chunk_type": chunk.get("chunk_type", ""),
                        "start_line": chunk.get("start_line", 1),
                        "end_line": chunk.get("end_line", 1),
                    }
                    ids_to_upsert.append(c_id)
                    vectors_to_upsert.append(vec)
                    metas_to_upsert.append(meta)
                    items_to_cache.append((ch, vec))

                # Save newly computed embeddings to cache
                await cache.save_embeddings(provider.model, items_to_cache)

            # Upsert into vector store
            vector_store.upsert(
                ids=ids_to_upsert, vectors=vectors_to_upsert, metadatas=metas_to_upsert
            )

        # 8. Rebuild BM25 index across all current chunks
        all_chunks = await self.chunk_repo.get_all_chunks(repo_id)
        bm25_manager = get_bm25_manager()
        new_bm25_dir = bm25_manager.get_index_dir(repo_id, new_commit_sha)
        new_index = BM25Index.build(all_chunks, new_bm25_dir)
        bm25_manager.put_index(repo_id, new_commit_sha, new_index)

        # 9. Atomically switch repository commit_sha & status
        total_loc = sum(f.get("loc", 0) for f in new_valid_files)
        await self.repo_repo.update_stats(
            repo_id,
            {
                "files_total": len(new_valid_files) + len(new_skipped_files),
                "files_indexed": len(new_valid_files),
                "files_skipped": len(new_skipped_files),
                "loc": total_loc,
                "chunks": len(all_chunks),
            },
        )
        await self.repo_repo.update_status(
            repo_id,
            status="ready",
            status_message=f"Synced successfully to commit {new_commit_sha[:7]}",
            commit_sha=new_commit_sha,
            indexed_model=provider.model,
        )

        # 10. Clean up old snapshot and old BM25 index
        if old_commit_sha and old_commit_sha != new_commit_sha:
            old_snapshot_path = (
                Path(self.settings.DATA_DIR) / "snapshots" / repo_id / old_commit_sha
            )
            if old_snapshot_path.exists():
                shutil.rmtree(old_snapshot_path, ignore_errors=True)
            bm25_manager.delete_index(repo_id, old_commit_sha)

        return {
            "status": "synced",
            "commit_sha": new_commit_sha,
            "message": f"Successfully synced {len(paths_to_process)} changed/added files.",
            "added_files": len(added_paths),
            "changed_files": len(changed_paths),
            "removed_files": len(removed_paths),
            "total_files": len(new_valid_files),
        }
