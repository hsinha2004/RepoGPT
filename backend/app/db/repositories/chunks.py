"""
Repository MongoDB operations for chunks collection (§6.2).
"""

from typing import Any

from bson import ObjectId
from pymongo import UpdateOne
from pymongo.asynchronous.collection import AsyncCollection

from app.db.mongo import get_collection


class ChunkRepository:
    def __init__(self, collection: AsyncCollection | None = None) -> None:
        self._col = collection if collection is not None else get_collection("chunks")

    async def bulk_upsert_chunks(
        self,
        repo_id: str | ObjectId,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Bulk upserts chunks for a repository."""
        if not chunks:
            return 0
        rid = str(repo_id)
        ops = []
        for c in chunks:
            doc = dict(c)
            doc["repo_id"] = rid
            chunk_id = doc.get("_id") or doc.get("chunk_id")
            if not chunk_id:
                # generate deterministic ID if missing
                import uuid

                chunk_id = str(uuid.uuid4())
            doc["_id"] = str(chunk_id)
            if "chunk_id" in doc:
                del doc["chunk_id"]

            ops.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {"$set": doc},
                    upsert=True,
                )
            )
        res = await self._col.bulk_write(ops, ordered=False)
        return res.upserted_count + res.modified_count

    async def get_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        """Retrieves a single chunk by its ID."""
        return await self._col.find_one({"_id": str(chunk_id)})

    async def list_for_file(
        self,
        repo_id: str | ObjectId,
        path: str,
    ) -> list[dict[str, Any]]:
        """Lists all chunks for a specific file ordered by start_line."""
        cursor = self._col.find({"repo_id": str(repo_id), "path": path}).sort("start_line", 1)
        return await cursor.to_list(length=1000)

    async def list_for_repo(
        self,
        repo_id: str | ObjectId,
        chunk_type: str | None = None,
        limit: int = 500,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """Lists chunks for a repository with optional chunk_type filter."""
        query: dict[str, Any] = {"repo_id": str(repo_id)}
        if chunk_type:
            query["chunk_type"] = chunk_type
        cursor = self._col.find(query).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_for_repo(self, repo_id: str | ObjectId) -> int:
        """Counts total chunks for a repository."""
        return await self._col.count_documents({"repo_id": str(repo_id)})

    async def delete_for_repo(self, repo_id: str | ObjectId) -> int:
        """Deletes all chunks for a repository."""
        res = await self._col.delete_many({"repo_id": str(repo_id)})
        return res.deleted_count
