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
from app.db.repositories.files import FileRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.repos import RepositoryRepository
from app.services.ingestion.archive import SafeArchiveExtractor
from app.services.ingestion.filter import IngestionFilter
from app.services.ingestion.github_fetcher import GitHubFetcher, parse_github_url

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        job_id: str,
        repo_id: str,
        repo_repo: RepositoryRepository | None = None,
        job_repo: JobRepository | None = None,
        file_repo: FileRepository | None = None,
    ) -> None:
        self.job_id = job_id
        self.repo_id = repo_id
        if repo_repo is not None and job_repo is not None and file_repo is not None:
            self.repo_repo = repo_repo
            self.job_repo = job_repo
            self.file_repo = file_repo
        else:
            db = get_database()
            self.repo_repo = repo_repo or RepositoryRepository(db.repositories)
            self.job_repo = job_repo or JobRepository(db.jobs)
            self.file_repo = file_repo or FileRepository(db.files, db.skipped_files)
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

            # In Milestone 2 exit criteria: "Fixture ZIP and a public GitHub repo ingest through 'filtering' with live progress"
            # Stages 4-10 (parsing, redacting, chunking, embedding, indexing, graph, overview) are built in M3-M6.
            # Here we mark the job and repository as successfully filtered and ready for AST parsing!
            counters = {
                "files_scanned": stats["files_total"],
                "files_kept": len(valid_files),
                "files_skipped": len(skipped_files),
                "loc": total_loc,
            }

            warnings = []
            if len(skipped_files) > 0:
                warnings.append(
                    f"Filtered out {len(skipped_files)} files (binaries, lockfiles, or ignored patterns)."
                )

            await self.emit_progress(
                stage="filtering",
                progress=20,
                message=f"Completed filtering: {len(valid_files)} source files indexed ({total_loc:,} lines).",
                counters=counters,
                warnings=warnings,
                status="succeeded",
            )

            await self.job_repo.mark_succeeded(self.job_id, counters=counters)
            await self.repo_repo.update_status(
                self.repo_id,
                status="ready",
                status_message=f"Repository ready ({len(valid_files)} files indexed)",
                commit_sha=commit_sha,
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
