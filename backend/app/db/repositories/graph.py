from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo import UpdateOne
from pymongo.asynchronous.collection import AsyncCollection

from app.db.mongo import get_collection


class GraphRepository:
    def __init__(self, collection: AsyncCollection | None = None) -> None:
        if collection is not None:
            self._col: AsyncCollection | None = collection
        else:
            try:
                self._col = get_collection("graph_edges")
            except Exception:
                self._col = None

    async def bulk_upsert_edges(
        self,
        repo_id: str | ObjectId,
        edges: list[dict[str, Any]],
    ) -> int:
        """Bulk upserts dependency and call edges for a repository."""
        if not edges or self._col is None:
            return 0
        rid = str(repo_id)
        ops = []
        for e in edges:
            doc = dict(e)
            doc["repo_id"] = rid
            source = doc["source"]
            target = doc["target"]
            edge_type = doc.get("type", "imports")
            ops.append(
                UpdateOne(
                    {"repo_id": rid, "source": source, "target": target, "type": edge_type},
                    {"$set": doc},
                    upsert=True,
                )
            )
        res = await self._col.bulk_write(ops, ordered=False)
        return res.upserted_count + res.modified_count

    async def get_neighbors(
        self,
        repo_id: str | ObjectId,
        paths: list[str],
    ) -> list[dict[str, Any]]:
        """Retrieves 1-hop outgoing and incoming edges for the given file paths."""
        if not paths or self._col is None:
            return []
        rid = str(repo_id)
        query = {
            "repo_id": rid,
            "$or": [
                {"source": {"$in": paths}},
                {"target": {"$in": paths}},
            ],
        }
        cursor = self._col.find(query)
        return await cursor.to_list(length=200)

    async def list_for_repo(
        self,
        repo_id: str | ObjectId,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        """Lists edges for a repository."""
        if self._col is None:
            return []
        cursor = self._col.find({"repo_id": str(repo_id)}).limit(limit)
        return await cursor.to_list(length=limit)

    async def delete_for_repo(self, repo_id: str | ObjectId) -> int:
        """Deletes all edges for a repository."""
        if self._col is None:
            return 0
        res = await self._col.delete_many({"repo_id": str(repo_id)})
        return res.deleted_count
