"""
Repository MongoDB operations for symbols collection (§6.2).
"""

from typing import Any

from bson import ObjectId
from pymongo import UpdateOne
from pymongo.asynchronous.collection import AsyncCollection

from app.db.mongo import get_collection


class SymbolRepository:
    def __init__(self, collection: AsyncCollection | None = None) -> None:
        self._col = collection if collection is not None else get_collection("symbols")

    async def bulk_upsert_symbols(
        self,
        repo_id: str | ObjectId,
        symbols: list[dict[str, Any]],
    ) -> int:
        """Bulk upserts symbol definitions for a repository."""
        if not symbols:
            return 0
        rid = str(repo_id)
        ops = []
        for s in symbols:
            doc = dict(s)
            doc["repo_id"] = rid
            doc["name_lower"] = doc["name"].lower()
            path = doc["path"]
            qname = doc["qualified_name"]
            ops.append(
                UpdateOne(
                    {"repo_id": rid, "path": path, "qualified_name": qname},
                    {"$set": doc},
                    upsert=True,
                )
            )
        res = await self._col.bulk_write(ops, ordered=False)
        return res.upserted_count + res.modified_count

    async def list_for_file(
        self,
        repo_id: str | ObjectId,
        path: str,
    ) -> list[dict[str, Any]]:
        """Lists all symbols defined in a specific file."""
        cursor = self._col.find({"repo_id": str(repo_id), "path": path}).sort("start_line", 1)
        return await cursor.to_list(length=500)

    async def search_by_name(
        self,
        repo_id: str | ObjectId,
        name: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Searches symbols by case-insensitive name."""
        name_lower = name.lower()
        cursor = (
            self._col.find({"repo_id": str(repo_id), "name_lower": name_lower})
            .sort("qualified_name", 1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def find_by_qualified_names(
        self,
        repo_id: str | ObjectId,
        qnames: list[str],
    ) -> list[dict[str, Any]]:
        """Finds symbols matching any of the qualified names."""
        if not qnames:
            return []
        cursor = self._col.find({"repo_id": str(repo_id), "qualified_name": {"$in": qnames}})
        return await cursor.to_list(length=100)

    async def find_by_name_lowers(
        self,
        repo_id: str | ObjectId,
        names: list[str],
    ) -> list[dict[str, Any]]:
        """Finds symbols matching any of the lowercase names."""
        if not names:
            return []
        lowers = [n.lower() for n in names]
        cursor = self._col.find({"repo_id": str(repo_id), "name_lower": {"$in": lowers}})
        return await cursor.to_list(length=100)

    async def search_by_prefix(
        self,
        repo_id: str | ObjectId,
        prefix: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Searches symbols whose lowercase name starts with prefix."""
        if not prefix:
            return []
        import re

        regex = f"^{re.escape(prefix.lower())}"
        cursor = (
            self._col.find({"repo_id": str(repo_id), "name_lower": {"$regex": regex}})
            .sort("qualified_name", 1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def delete_by_files(self, repo_id: str | ObjectId, paths: list[str]) -> int:
        """Deletes symbols belonging to a specific list of file paths."""
        if not paths:
            return 0
        res = await self._col.delete_many({"repo_id": str(repo_id), "path": {"$in": paths}})
        return res.deleted_count

    async def count_for_repo(self, repo_id: str | ObjectId) -> int:
        """Counts total symbols for a repository."""
        return await self._col.count_documents({"repo_id": str(repo_id)})

    async def list_for_repo(
        self,
        repo_id: str | ObjectId,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        """Retrieves symbols for a repository."""
        cursor = self._col.find({"repo_id": str(repo_id)}).limit(limit)
        return await cursor.to_list(length=limit)

    async def delete_for_repo(self, repo_id: str | ObjectId) -> int:
        """Deletes all symbols for a repository."""
        res = await self._col.delete_many({"repo_id": str(repo_id)})
        return res.deleted_count
