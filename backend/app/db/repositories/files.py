"""
Repository MongoDB operations for files and skipped_files collections (§6.2).
"""

from typing import Any

from bson import ObjectId
from pymongo import UpdateOne
from pymongo.asynchronous.collection import AsyncCollection

from app.db.mongo import get_collection


class FileRepository:
    def __init__(
        self,
        files_col: AsyncCollection | None = None,
        skipped_col: AsyncCollection | None = None,
    ) -> None:
        self._files = files_col if files_col is not None else get_collection("files")
        self._skipped = skipped_col if skipped_col is not None else get_collection("skipped_files")

    async def upsert_files(self, repo_id: str | ObjectId, files: list[dict[str, Any]]) -> int:
        """Bulk upserts file documents for a repository."""
        if not files:
            return 0
        rid = str(repo_id)
        ops = []
        for f in files:
            f_copy = dict(f)
            f_copy["repo_id"] = rid
            path = f_copy["path"]
            ops.append(
                UpdateOne(
                    {"repo_id": rid, "path": path},
                    {"$set": f_copy},
                    upsert=True,
                )
            )
        res = await self._files.bulk_write(ops, ordered=False)
        return res.upserted_count + res.modified_count

    async def insert_skipped_files(
        self,
        repo_id: str | ObjectId,
        skipped: list[dict[str, Any]],
    ) -> int:
        """Records skipped/filtered files for audit and visibility."""
        if not skipped:
            return 0
        rid = str(repo_id)
        docs = []
        for s in skipped:
            item = dict(s)
            item["repo_id"] = rid
            docs.append(item)
        res = await self._skipped.insert_many(docs, ordered=False)
        return len(res.inserted_ids)

    async def get_file(self, repo_id: str | ObjectId, path: str) -> dict[str, Any] | None:
        """Retrieves a single file record by path within a repository."""
        return await self._files.find_one({"repo_id": str(repo_id), "path": path})

    async def list_files(
        self,
        repo_id: str | ObjectId,
        kind: str | None = None,
        language: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Lists files for a repository with optional kind and language filters."""
        query: dict[str, Any] = {"repo_id": str(repo_id)}
        if kind:
            query["kind"] = kind
        if language:
            query["language"] = language

        cursor = self._files.find(query).sort("path", 1).limit(limit)
        return await cursor.to_list(length=limit)

    async def list_skipped(self, repo_id: str | ObjectId) -> list[dict[str, Any]]:
        """Lists all files that were skipped during ingestion."""
        cursor = self._skipped.find({"repo_id": str(repo_id)}).sort("path", 1)
        return await cursor.to_list(length=2000)

    async def delete_for_repo(self, repo_id: str | ObjectId) -> tuple[int, int]:
        """Deletes all file and skipped file records for a repository."""
        rid = str(repo_id)
        del_files = await self._files.delete_many({"repo_id": rid})
        del_skipped = await self._skipped.delete_many({"repo_id": rid})
        return del_files.deleted_count, del_skipped.deleted_count

    async def delete_by_paths(self, repo_id: str | ObjectId, paths: list[str]) -> int:
        """Deletes file records by list of paths for a repository."""
        if not paths:
            return 0
        res = await self._files.delete_many({"repo_id": str(repo_id), "path": {"$in": paths}})
        return res.deleted_count

    async def count_files(self, repo_id: str | ObjectId) -> int:
        """Counts total indexed files for a repository."""
        return await self._files.count_documents({"repo_id": str(repo_id)})

    async def list_top_pagerank_files(
        self,
        repo_id: str | ObjectId,
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Retrieves top files by PageRank metric."""
        cursor = (
            self._files.find({"repo_id": str(repo_id)}).sort("metrics.pagerank", -1).limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def bulk_update_metrics(
        self,
        repo_id: str | ObjectId,
        metrics_by_path: dict[str, dict[str, Any]],
    ) -> int:
        """Updates file metrics (pagerank, fan_in, fan_out, in_cycle, is_orphan)."""
        if not metrics_by_path:
            return 0
        rid = str(repo_id)
        ops = []
        for path, m in metrics_by_path.items():
            ops.append(
                UpdateOne(
                    {"repo_id": rid, "path": path},
                    {"$set": {"metrics": m}},
                )
            )
        res = await self._files.bulk_write(ops, ordered=False)
        return res.modified_count
