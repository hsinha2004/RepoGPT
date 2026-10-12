"""
Ingestion pipeline orchestrator (§8.11).
Coordinates stages: fetching (10) -> extracting (5) -> filtering (5) -> [parsing -> redacting -> chunking -> embedding -> indexing -> graph -> overview].
Emits progress events over Redis pub/sub 'job:{job_id}' and persists to Mongo.
"""

import json
import os
from typing import Any

import structlog

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.mongo import get_database
from app.db.redis import get_redis_client
from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository
from app.db.repositories.graph import GraphRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.overview import OverviewRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.symbols import SymbolRepository
from app.services.analysis.entry_points import EntryPointDetector
from app.services.analysis.overview import OverviewService
from app.services.analysis.reading_order import ReadingOrderGenerator
from app.services.analysis.tech_stack import TechStackDetector
from app.services.chunking.chunker import CodeChunker
from app.services.graph.analyzer import GraphAnalyzer
from app.services.graph.builder import GraphBuilder
from app.services.indexing.embeddings.cache import EmbeddingCache
from app.services.indexing.embeddings.factory import get_embedding_provider
from app.services.indexing.vector.factory import get_vector_store
from app.services.ingestion.archive import SafeArchiveExtractor
from app.services.ingestion.filter import IngestionFilter
from app.services.ingestion.github_fetcher import GitHubFetcher, parse_github_url
from app.services.keyword.bm25_index import BM25Index, get_bm25_manager
from app.services.llm.factory import get_llm_provider
from app.services.parsing.models import ParsedFile
from app.services.parsing.registry import ParserRegistry
from app.services.redaction.redactor import SecretRedactor

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        job_id: str,
        repo_id: str,
        repo_repo: RepositoryRepository | None = None,
        job_repo: JobRepository | None = None,
        file_repo: FileRepository | None = None,
        symbol_repo: SymbolRepository | None = None,
        chunk_repo: ChunkRepository | None = None,
        graph_repo: GraphRepository | None = None,
        overview_repo: OverviewRepository | None = None,
        cache: EmbeddingCache | None = None,
    ) -> None:
        self.job_id = job_id
        self.repo_id = repo_id
        self.cache = cache
        db = None
        if (
            repo_repo is None
            or job_repo is None
            or file_repo is None
            or symbol_repo is None
            or chunk_repo is None
            or graph_repo is None
            or overview_repo is None
        ):
            try:
                db = get_database()
            except Exception:
                db = None
        self.repo_repo = repo_repo or (
            RepositoryRepository(db.repositories) if db is not None else RepositoryRepository()
        )
        self.job_repo = job_repo or (JobRepository(db.jobs) if db is not None else JobRepository())
        self.file_repo = file_repo or (
            FileRepository(db.files, db.skipped_files) if db is not None else FileRepository()
        )
        self.symbol_repo = symbol_repo or (
            SymbolRepository(db.symbols) if db is not None else SymbolRepository()
        )
        self.chunk_repo = chunk_repo or (
            ChunkRepository(db.chunks) if db is not None else ChunkRepository()
        )
        self.graph_repo = graph_repo or (
            GraphRepository(db.graph_edges) if db is not None else GraphRepository()
        )
        self.overview_repo = overview_repo or (
            OverviewRepository(db.repo_overviews) if db is not None else OverviewRepository()
        )
        self.settings = get_settings()

    async def emit_progress(
        self,
        stage: str,
        progress: int,
        message: str,
        counters: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        status: str = "running",
    ) -> None:
        """Publishes progress update to Redis pub/sub and persists to Mongo."""
        await self.job_repo.update_progress(
            job_id=self.job_id,
            stage=stage,
            progress=progress,
            message=message,
            counters=counters,
            warnings=warnings,
        )

        event_payload = {
            "job_id": self.job_id,
            "repo_id": self.repo_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "counters": counters or {},
            "warnings": warnings or [],
            "status": status,
        }
        try:
            redis = get_redis_client()
            await redis.publish(f"job:{self.job_id}", json.dumps(event_payload))
        except Exception:
            pass

    async def check_cancellation(self) -> None:
        """Checks if cancellation was requested for this job."""
        if await self.job_repo.is_cancel_requested(self.job_id):
            await self.job_repo.mark_cancelled(self.job_id)
            await self.repo_repo.update_status(
                self.repo_id, "failed", status_message="Ingestion cancelled by user"
            )
            raise AppError("Ingestion cancelled by user request", code="CANCELLED")

    async def run(
        self, archive_file_path: str | None = None, github_pat: str | None = None
    ) -> dict[str, Any]:
        """
        Executes the ingestion pipeline.
        For GitHub repositories: fetches metadata, resolves SHA, downloads tarball, extracts, filters.
        For ZIP uploads: verifies archive, extracts, filters.
        """
        await self.job_repo.mark_running(self.job_id, stage="fetching")
        await self.repo_repo.update_status(
            self.repo_id, "processing", status_message="Ingestion in progress"
        )

        repo_doc = await self.repo_repo.get_by_id(self.repo_id)
        if not repo_doc:
            raise AppError(f"Repository {self.repo_id} not found in database", code="NOT_FOUND")

        source = repo_doc.get("source", {})
        source_type = source.get("type", "github")
        commit_sha: str = repo_doc.get("commit_sha") or "main"
        temp_archive_path = archive_file_path

        try:
            # ================= STAGE 1: FETCHING (0 -> 10%) =================
            await self.emit_progress(
                stage="fetching",
                progress=2,
                message="Fetching repository metadata and sources...",
            )

            if source_type == "github":
                gh_url = (
                    source.get("url")
                    or f"https://github.com/{source.get('owner')}/{source.get('name')}"
                )
                owner, repo_name, ref = parse_github_url(gh_url)
                fetcher = GitHubFetcher(pat=github_pat)

                meta = await fetcher.fetch_repo_metadata(owner, repo_name)
                effective_ref = ref or source.get("ref") or meta.get("default_branch") or "main"
                commit_sha = await fetcher.resolve_commit_sha(owner, repo_name, effective_ref)

                # Update repo with resolved details
                await self.repo_repo.update_status(
                    self.repo_id,
                    status="processing",
                    status_message=f"Fetched {owner}/{repo_name} @ {commit_sha[:7]}",
                    commit_sha=commit_sha,
                )

                # Download tarball
                tarball_dir = os.path.join(self.settings.DATA_DIR, "uploads", "tmp")
                os.makedirs(tarball_dir, exist_ok=True)
                temp_archive_path = os.path.join(tarball_dir, f"{self.repo_id}_{commit_sha}.tar.gz")

                await self.emit_progress(
                    stage="fetching",
                    progress=6,
                    message=f"Downloading archive from GitHub (@{commit_sha[:7]})...",
                )
                await fetcher.download_tarball(owner, repo_name, commit_sha, temp_archive_path)

            elif source_type == "upload":
                if not temp_archive_path or not os.path.exists(temp_archive_path):
                    raise AppError(
                        "Uploaded archive file not found on disk.", code="FILE_NOT_FOUND"
                    )
                # Generate deterministic snapshot commit_sha from file content if not set
                import hashlib

                with open(temp_archive_path, "rb") as archive_file:
                    file_hash = hashlib.sha256(archive_file.read(65536)).hexdigest()[:16]
                commit_sha = f"upload_{file_hash}"
                await self.repo_repo.update_status(
                    self.repo_id,
                    status="processing",
                    status_message="Verifying uploaded archive",
                    commit_sha=commit_sha,
                )

            await self.check_cancellation()

            # ================= STAGE 2: EXTRACTING (10 -> 15%) =================
            await self.emit_progress(
                stage="extracting",
                progress=10,
                message="Safely extracting codebase archive...",
            )

            if not temp_archive_path or not os.path.exists(temp_archive_path):
                raise AppError("Archive file not found for extraction.", code="FILE_NOT_FOUND")

            snapshot_dir = os.path.join(
                self.settings.DATA_DIR, "snapshots", self.repo_id, commit_sha
            )
            extractor = SafeArchiveExtractor()

            if (
                temp_archive_path.endswith(".tar.gz")
                or temp_archive_path.endswith(".tar")
                or source_type == "github"
            ):
                extractor.extract_tar(temp_archive_path, snapshot_dir, strip_root_dir=True)
            else:
                extractor.extract_zip(temp_archive_path, snapshot_dir, strip_root_dir=False)

            await self.check_cancellation()

            # ================= STAGE 3: FILTERING (15 -> 20%) =================
            await self.emit_progress(
                stage="filtering",
                progress=15,
                message="Filtering files and applying ignore rules...",
            )

            extra_ignores = repo_doc.get("settings", {}).get("extra_ignore_patterns", [])
            file_filter = IngestionFilter(snapshot_dir, extra_ignore_patterns=extra_ignores)
            valid_files, skipped_files = file_filter.scan_and_filter()

            # Persist files and skipped files into Mongo
            for file_doc in valid_files:
                file_doc["commit_sha"] = commit_sha
            await self.file_repo.upsert_files(self.repo_id, valid_files)
            await self.file_repo.insert_skipped_files(self.repo_id, skipped_files)

            # Compute languages and statistics
            languages: dict[str, int] = {}
            total_loc = 0
            for file_doc in valid_files:
                lang = file_doc.get("language", "generic")
                loc = file_doc.get("loc", 0)
                total_loc += loc
                languages[lang] = languages.get(lang, 0) + loc

            stats = {
                "files_total": len(valid_files) + len(skipped_files),
                "files_indexed": len(valid_files),
                "files_skipped": len(skipped_files),
                "loc": total_loc,
                "symbols": 0,
                "chunks": 0,
                "languages": languages,
                "redactions": 0,
            }
            await self.repo_repo.update_stats(self.repo_id, stats)

            # ================= STAGE 4: PARSING (20 -> 35%) =================
            await self.emit_progress(
                stage="parsing",
                progress=20,
                message=f"Parsing AST and symbols for {len(valid_files)} files...",
            )
            parser_registry = ParserRegistry()
            parsed_files_map: dict[str, ParsedFile] = {}
            raw_content_map: dict[str, str] = {}
            all_symbols_to_upsert: list[dict[str, Any]] = []
            warnings: list[str] = []
            if len(skipped_files) > 0:
                warnings.append(
                    f"Filtered out {len(skipped_files)} files (binaries, lockfiles, or ignored patterns)."
                )

            for file_doc in valid_files:
                f_path = file_doc["path"]
                disk_path = os.path.join(snapshot_dir, f_path)
                try:
                    with open(disk_path, encoding="utf-8", errors="replace") as f_src:
                        source_code = f_src.read()
                except Exception:
                    source_code = ""

                raw_content_map[f_path] = source_code
                parsed = parser_registry.parse_file(source_code, f_path, file_doc.get("language"))
                parsed_files_map[f_path] = parsed
                if parsed.warnings:
                    warnings.extend(parsed.warnings)

                # Update file_doc with card, symbols_count, imports, is_entry_point
                file_doc["symbols_count"] = len(parsed.symbols)
                file_doc["imports"] = parsed.imports
                file_doc["card"] = parsed.card
                file_doc["is_entry_point"] = len(parsed.entry_point_hints) > 0

                for s in parsed.symbols:
                    all_symbols_to_upsert.append(s.to_dict(repo_id=self.repo_id, path=f_path))

            # Upsert updated file docs and all symbols
            await self.file_repo.upsert_files(self.repo_id, valid_files)
            if all_symbols_to_upsert:
                await self.symbol_repo.bulk_upsert_symbols(self.repo_id, all_symbols_to_upsert)

            await self.check_cancellation()

            # ================= STAGE 5: REDACTING (35 -> 40%) =================
            await self.emit_progress(
                stage="redacting",
                progress=35,
                message="Scanning and redacting credentials...",
                counters={
                    "files_parsed": len(valid_files),
                    "symbols_found": len(all_symbols_to_upsert),
                },
            )
            redactor = SecretRedactor()
            redacted_content_map: dict[str, str] = {}
            total_redactions = 0

            for file_doc in valid_files:
                f_path = file_doc["path"]
                raw_code = raw_content_map.get(f_path, "")
                redact_res = redactor.redact(raw_code)
                redacted_content_map[f_path] = redact_res.redacted_text
                file_doc["redaction_count"] = redact_res.redaction_count
                total_redactions += redact_res.redaction_count

            # Update file redaction counts
            await self.file_repo.upsert_files(self.repo_id, valid_files)

            await self.check_cancellation()

            # ================= STAGE 6: CHUNKING (40 -> 45%) =================
            await self.emit_progress(
                stage="chunking",
                progress=40,
                message="Generating code-aware chunks, skeletons, and summaries...",
                counters={
                    "files_scanned": len(valid_files),
                    "redactions_found": total_redactions,
                },
            )
            chunker = CodeChunker()
            all_chunks_to_upsert: list[dict[str, Any]] = []

            for file_doc in valid_files:
                f_path = file_doc["path"]
                parsed = parsed_files_map[f_path]
                redacted_text = redacted_content_map[f_path]
                file_chunks = chunker.chunk_file(
                    parsed_file=parsed,
                    redacted_source=redacted_text,
                    repo_id=self.repo_id,
                    commit_sha=commit_sha,
                )
                all_chunks_to_upsert.extend(file_chunks)

            # Directory summary chunks
            dir_summaries = chunker.build_directory_summaries(
                parsed_files=list(parsed_files_map.values()),
                repo_id=self.repo_id,
                commit_sha=commit_sha,
            )
            all_chunks_to_upsert.extend(dir_summaries)

            if all_chunks_to_upsert:
                await self.chunk_repo.bulk_upsert_chunks(self.repo_id, all_chunks_to_upsert)

            stats = {
                "files_total": len(valid_files) + len(skipped_files),
                "files_indexed": len(valid_files),
                "files_skipped": len(skipped_files),
                "loc": total_loc,
                "symbols": len(all_symbols_to_upsert),
                "chunks": len(all_chunks_to_upsert),
                "languages": languages,
                "redactions": total_redactions,
            }
            await self.repo_repo.update_stats(self.repo_id, stats)

            counters = {
                "files_scanned": stats["files_total"],
                "files_kept": len(valid_files),
                "files_skipped": len(skipped_files),
                "loc": total_loc,
                "symbols": len(all_symbols_to_upsert),
                "chunks": len(all_chunks_to_upsert),
                "redactions": total_redactions,
            }

            await self.emit_progress(
                stage="chunking",
                progress=45,
                message=(
                    f"Completed parsing & chunking: {len(valid_files)} files, "
                    f"{len(all_symbols_to_upsert)} symbols, {len(all_chunks_to_upsert)} chunks."
                ),
                counters=counters,
                warnings=warnings,
            )

            await self.check_cancellation()

            # ================= STAGE 7: EMBEDDING (45 -> 80%) =================
            await self.emit_progress(
                stage="embedding",
                progress=45,
                message=f"Computing code embeddings for {len(all_chunks_to_upsert)} chunks...",
                counters={
                    "chunks_total": len(all_chunks_to_upsert),
                    "chunks_embedded": 0,
                },
            )
            embed_cfg = repo_doc.get("embedding", {})
            provider_name = embed_cfg.get("provider", self.settings.EMBEDDING_PROVIDER)
            model_name = embed_cfg.get("model", self.settings.EMBEDDING_MODEL)
            provider = get_embedding_provider(provider_name, model=model_name)
            cache = self.cache or EmbeddingCache()

            # Check cache for existing embeddings
            content_hashes = [c["content_hash"] for c in all_chunks_to_upsert]
            cached_vectors = await cache.get_cached_embeddings(provider.model, content_hashes)

            chunk_vectors: list[list[float]] = []
            chunk_vector_ids: list[str] = []
            chunk_metas: list[dict[str, Any]] = []

            missing_chunks: list[dict[str, Any]] = []

            for chunk in all_chunks_to_upsert:
                c_id = str(chunk.get("_id") or chunk.get("chunk_id"))
                ch = chunk["content_hash"]
                meta = {
                    "path": chunk.get("path", ""),
                    "chunk_type": chunk.get("chunk_type", ""),
                    "start_line": chunk.get("start_line", 1),
                    "end_line": chunk.get("end_line", 1),
                }
                if ch in cached_vectors:
                    chunk_vector_ids.append(c_id)
                    chunk_vectors.append(cached_vectors[ch])
                    chunk_metas.append(meta)
                else:
                    missing_chunks.append(chunk)

            # Embed missing in batches
            batch_size = provider.batch_size or 32
            embedded_so_far = len(chunk_vectors)
            total_chunks = len(all_chunks_to_upsert)

            for b_start in range(0, len(missing_chunks), batch_size):
                await self.check_cancellation()
                b_end = min(b_start + batch_size, len(missing_chunks))
                batch = missing_chunks[b_start:b_end]
                batch_texts = [c.get("embed_text") or c.get("text", "") for c in batch]

                vectors = provider.embed_documents(batch_texts)

                to_cache: list[tuple[str, list[float]]] = []
                for chunk, vec in zip(batch, vectors, strict=False):
                    c_id = str(chunk.get("_id") or chunk.get("chunk_id"))
                    ch = chunk["content_hash"]
                    meta = {
                        "path": chunk.get("path", ""),
                        "chunk_type": chunk.get("chunk_type", ""),
                        "start_line": chunk.get("start_line", 1),
                        "end_line": chunk.get("end_line", 1),
                    }
                    chunk_vector_ids.append(c_id)
                    chunk_vectors.append(vec)
                    chunk_metas.append(meta)
                    to_cache.append((ch, vec))

                await cache.save_embeddings(provider.model, to_cache)
                embedded_so_far += len(batch)

                progress_val = 45 + int(35 * (embedded_so_far / max(1, total_chunks)))
                await self.emit_progress(
                    stage="embedding",
                    progress=progress_val,
                    message=f"Embedded {embedded_so_far}/{total_chunks} chunks...",
                    counters={
                        "chunks_total": total_chunks,
                        "chunks_embedded": embedded_so_far,
                    },
                )

            await self.check_cancellation()

            # ================= STAGE 8: INDEXING (80 -> 90%) =================
            await self.emit_progress(
                stage="indexing",
                progress=80,
                message="Building vector index and code-aware BM25 keyword index...",
            )

            # 1. Vector Store upsert
            vector_store = get_vector_store(
                store_type=self.settings.VECTOR_STORE,
                repo_id=self.repo_id,
                model_slug=provider.model,
            )
            if chunk_vector_ids:
                vector_store.upsert(
                    ids=chunk_vector_ids,
                    vectors=chunk_vectors,
                    metadatas=chunk_metas,
                )

            # 2. BM25 keyword index
            bm25_manager = get_bm25_manager()
            bm25_dir = bm25_manager.get_index_dir(self.repo_id, commit_sha)
            bm25_index = BM25Index.build(all_chunks_to_upsert, bm25_dir)
            bm25_manager.put_index(self.repo_id, commit_sha, bm25_index)

            await self.check_cancellation()
            await self.emit_progress(
                stage="indexing",
                progress=90,
                message=f"Indexes built successfully: {len(chunk_vector_ids)} vectors, {len(all_chunks_to_upsert)} BM25 docs.",
            )

            # ================= STAGE 9: GRAPH (90 -> 95%) =================
            await self.emit_progress(
                stage="graph",
                progress=90,
                message="Constructing dependency graph and computing centrality metrics...",
            )

            # Build symbols_by_file map
            symbols_by_file: dict[str, list[dict[str, Any]]] = {}
            for sym_doc in all_symbols_to_upsert:
                symbols_by_file.setdefault(sym_doc.get("path", ""), []).append(sym_doc)

            # Detect Go module name if go.mod exists
            go_mod_module = ""
            for f_doc in valid_files:
                if f_doc.get("path") == "go.mod":
                    go_disk = os.path.join(snapshot_dir, "go.mod")
                    if os.path.exists(go_disk):
                        try:
                            with open(go_disk, encoding="utf-8", errors="ignore") as gf:
                                for line in gf:
                                    sline = line.strip()
                                    if sline.startswith("module "):
                                        go_mod_module = sline.split(maxsplit=1)[1].strip()
                                        break
                        except Exception:
                            pass
                    break

            builder = GraphBuilder()
            edges = builder.build_edges(
                files=valid_files,
                symbols_by_file=symbols_by_file,
                go_module=go_mod_module,
            )

            await self.graph_repo.delete_for_repo(self.repo_id)
            if edges:
                await self.graph_repo.bulk_upsert_edges(self.repo_id, edges)

            all_paths = [f["path"] for f in valid_files]
            analyzer = GraphAnalyzer(edges, all_paths)
            file_metrics = analyzer.compute_file_metrics()
            await self.file_repo.bulk_update_metrics(self.repo_id, file_metrics)

            await self.check_cancellation()
            await self.emit_progress(
                stage="graph",
                progress=95,
                message=f"Dependency graph constructed ({len(edges)} edges) and centrality metrics calculated.",
            )

            # ================= STAGE 10: OVERVIEW (95 -> 100%) =================
            await self.emit_progress(
                stage="overview",
                progress=95,
                message="Generating architectural overview and onboarding tour...",
            )

            files_with_content = []
            for f_doc in valid_files:
                f_copy = dict(f_doc)
                f_copy["content"] = raw_content_map.get(f_doc["path"], "")
                files_with_content.append(f_copy)

            tech_detector = TechStackDetector()
            tech_stack = tech_detector.detect(files_with_content, languages)

            ep_detector = EntryPointDetector()
            entry_points = ep_detector.detect(files_with_content)

            ro_gen = ReadingOrderGenerator()
            reading_order = ro_gen.generate(all_paths, entry_points, file_metrics, edges)

            readme_text = ""
            for f_doc in valid_files:
                if f_doc.get("path", "").lower() in ("readme.md", "readme", "readme.txt"):
                    readme_text = raw_content_map.get(f_doc["path"], "")
                    break

            top_files = sorted(
                valid_files,
                key=lambda f: file_metrics.get(f["path"], {}).get("pagerank", 0.0),
                reverse=True,
            )

            llm = get_llm_provider()
            overview_service = OverviewService(llm)
            overview_data = await overview_service.generate_overview(
                repo_name=repo_doc.get("display_name") or repo_doc.get("name") or "Repository",
                commit_sha=commit_sha,
                readme_text=readme_text,
                tech_stack=tech_stack,
                entry_points=entry_points,
                reading_order=reading_order,
                file_metrics=file_metrics,
                top_files=top_files[:15],
            )
            await self.overview_repo.upsert(self.repo_id, commit_sha, overview_data)

            await self.check_cancellation()
            await self.emit_progress(
                stage="overview",
                progress=100,
                message="Repository indexing, dependency graph, and architectural overview complete.",
                status="succeeded",
            )

            await self.job_repo.mark_succeeded(self.job_id, counters=counters)
            await self.repo_repo.update_status(
                self.repo_id,
                status="ready",
                status_message=(
                    f"Repository ready ({len(valid_files)} files, "
                    f"{len(all_symbols_to_upsert)} symbols, {len(all_chunks_to_upsert)} chunks indexed)"
                ),
                commit_sha=commit_sha,
                indexed_model=provider.model,
            )

            # Cleanup temp archive if created
            if (
                temp_archive_path
                and os.path.exists(temp_archive_path)
                and "uploads" in temp_archive_path
            ):
                try:
                    os.remove(temp_archive_path)
                except Exception:
                    pass

            return {
                "repo_id": self.repo_id,
                "commit_sha": commit_sha,
                "files_count": len(valid_files),
                "skipped_count": len(skipped_files),
                "loc": total_loc,
            }

        except Exception as e:
            logger.exception(
                "ingestion_pipeline_failed", job_id=self.job_id, repo_id=self.repo_id, error=str(e)
            )
            err_code = getattr(e, "code", "INGESTION_ERROR")
            err_msg = str(e)
            await self.job_repo.mark_failed(self.job_id, code=err_code, message=err_msg)
            await self.repo_repo.update_status(self.repo_id, "failed", status_message=err_msg)
            # Cleanup temp files on failure
            if (
                temp_archive_path
                and os.path.exists(temp_archive_path)
                and "uploads" in temp_archive_path
            ):
                try:
                    os.remove(temp_archive_path)
                except Exception:
                    pass
            raise
