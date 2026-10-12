from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.db.mongo import get_collection

_MEMORY_BENCHMARKS: dict[str, dict[str, Any]] = {}


class BenchmarkRepository:
    """Repository for persisting, caching, and serving evaluation benchmarks (§14.1)."""

    def __init__(self, collection: AsyncCollection | None = None) -> None:
        if collection is not None:
            self._col: AsyncCollection | None = collection
        else:
            try:
                self._col = get_collection("benchmarks")
            except Exception:
                self._col = None

    def _get_builtin_benchmarks_from_disk(self) -> list[dict[str, Any]]:
        """Loads built-in benchmarks directly from eval/benchmarks/."""
        benchmarks: list[dict[str, Any]] = []
        possible_dirs = [
            Path("eval/benchmarks"),
            Path("../eval/benchmarks"),
            Path(__file__).resolve().parent.parent.parent.parent / "eval" / "benchmarks",
            Path(os.getcwd()) / "eval" / "benchmarks",
        ]
        target_dir = next((d for d in possible_dirs if d.exists()), None)
        if not target_dir:
            return benchmarks

        for yf in sorted(target_dir.glob("*.yaml")):
            try:
                with open(yf, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict) and "name" in data:
                        b_id = f"builtin:{data['name']}"
                        questions = data.get("questions", [])
                        benchmarks.append(
                            {
                                "_id": b_id,
                                "id": b_id,
                                "name": data["name"],
                                "description": data.get("description", ""),
                                "repo": data.get("repo", {}),
                                "questions": questions,
                                "question_count": len(questions),
                                "is_builtin": True,
                                "created_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                            }
                        )
            except Exception:
                pass
        return benchmarks

    async def list_benchmarks(self, owner_id: str | None = None) -> list[dict[str, Any]]:
        """Lists all built-in benchmarks plus user-created benchmarks."""
        builtins = self._get_builtin_benchmarks_from_disk()

        if self._col is None:
            user_b = [
                b
                for b in _MEMORY_BENCHMARKS.values()
                if not owner_id or b.get("owner_id") == owner_id
            ]
            return builtins + user_b

        try:
            query: dict[str, Any] = {"$or": [{"is_builtin": True}]}
            if owner_id:
                query["$or"].append({"owner_id": owner_id})
            cursor = self._col.find(query)
            db_benchmarks: list[dict[str, Any]] = await cursor.to_list(length=100)

            # Deduplicate by name
            db_names = {b.get("name") for b in db_benchmarks}
            combined = list(db_benchmarks)
            for b in builtins:
                if b.get("name") not in db_names:
                    combined.append(b)

            # Format IDs
            for item in combined:
                if "_id" in item:
                    item["id"] = str(item["_id"])
                    item["question_count"] = len(item.get("questions", []))
            return combined
        except Exception:
            return builtins

    async def get_benchmark(self, benchmark_id: str) -> dict[str, Any] | None:
        """Retrieves a benchmark by ID or name (supporting built-ins)."""
        builtins = self._get_builtin_benchmarks_from_disk()
        for b in builtins:
            if b["id"] == benchmark_id or b["name"] == benchmark_id or b["_id"] == benchmark_id:
                return b

        if self._col is None:
            return _MEMORY_BENCHMARKS.get(benchmark_id)

        try:
            query: dict[str, Any] = {}
            if ObjectId.is_valid(benchmark_id):
                query = {
                    "$or": [
                        {"_id": ObjectId(benchmark_id)},
                        {"id": benchmark_id},
                        {"name": benchmark_id},
                    ]
                }
            else:
                query = {"$or": [{"id": benchmark_id}, {"name": benchmark_id}]}

            doc = await self._col.find_one(query)
            if doc:
                doc["id"] = str(doc["_id"])
                doc["question_count"] = len(doc.get("questions", []))
                return doc
        except Exception:
            pass

        return None

    async def create_benchmark(
        self,
        name: str,
        description: str,
        repo: dict[str, Any],
        questions: list[dict[str, Any]],
        owner_id: str,
    ) -> dict[str, Any]:
        """Creates and stores a custom uploaded benchmark."""
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "name": name,
            "description": description,
            "repo": repo,
            "questions": questions,
            "question_count": len(questions),
            "is_builtin": False,
            "owner_id": owner_id,
            "created_at": now.isoformat(),
        }

        if self._col is not None:
            res = await self._col.insert_one(doc)
            doc["_id"] = res.inserted_id
            doc["id"] = str(res.inserted_id)
        else:
            oid = ObjectId()
            doc["_id"] = oid
            doc["id"] = str(oid)
            _MEMORY_BENCHMARKS[str(oid)] = doc

        return doc

    async def delete_benchmark(self, benchmark_id: str, owner_id: str) -> bool:
        """Deletes a custom user benchmark (built-ins cannot be deleted)."""
        if benchmark_id.startswith("builtin:"):
            return False

        if self._col is None:
            bench = _MEMORY_BENCHMARKS.get(benchmark_id)
            if bench and bench.get("owner_id") == owner_id:
                del _MEMORY_BENCHMARKS[benchmark_id]
                return True
            return False

        try:
            filter_query: dict[str, Any] = {
                "owner_id": owner_id,
                "is_builtin": False,
            }
            if ObjectId.is_valid(benchmark_id):
                filter_query["_id"] = ObjectId(benchmark_id)
            else:
                filter_query["id"] = benchmark_id

            res = await self._col.delete_one(filter_query)
            return bool(res.deleted_count > 0)
        except Exception:
            return False
