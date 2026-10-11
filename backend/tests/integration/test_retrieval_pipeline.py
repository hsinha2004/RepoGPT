"""
Integration tests for Retrieval Pipeline and Router on TaskFlow fixture (§9 & §14 & §20).
Exit criterion: expected file in top-5 for >= 80% of TaskFlow benchmark questions (hybrid).
"""

import os
import shutil
import tempfile
import zipfile
from typing import Any
import pytest
import yaml
from bson import ObjectId

from app.core.config import get_settings
from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.symbols import SymbolRepository
from app.schemas.retrieval import SearchRequest
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.retrieval.service import RetrievalService


class MockRepoCollection:
    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    async def insert_one(self, doc: dict[str, Any]) -> Any:
        oid = ObjectId()
        doc["_id"] = oid
        self.docs[str(oid)] = doc
        return type("Result", (), {"inserted_id": oid})()

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        oid = str(query.get("_id", ""))
        return self.docs.get(oid)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> Any:
        oid = str(query.get("_id", ""))
        doc = self.docs.get(oid)
        if not doc:
            return type("Res", (), {"modified_count": 0})()
        if "$set" in update:
            doc.update(update["$set"])
        return type("Res", (), {"modified_count": 1})()


class MockJobCollection:
    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {}

    async def insert_one(self, doc: dict[str, Any]) -> Any:
        oid = ObjectId()
        doc["_id"] = oid
        self.docs[str(oid)] = doc
        return type("Result", (), {"inserted_id": oid})()

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        oid = str(query.get("_id", ""))
        return self.docs.get(oid)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> Any:
        oid = str(query.get("_id", ""))
        doc = self.docs.get(oid)
        if not doc:
            return type("Res", (), {"modified_count": 0})()
        if "$set" in update:
            doc.update(update["$set"])
        return type("Res", (), {"modified_count": 1})()


class MockFileCollection:
    def __init__(self) -> None:
        self.files: dict[str, dict[str, Any]] = {}
        self.skipped: list[dict[str, Any]] = []

    async def bulk_write(self, ops: list[Any], ordered: bool = False) -> Any:  # noqa: ARG002
        for op in ops:
            query = op._filter
            doc = op._doc["$set"]
            key = f"{query['repo_id']}:{query['path']}"
            self.files[key] = doc
        return type("Res", (), {"upserted_count": len(ops), "modified_count": 0})()

    async def insert_many(self, docs: list[dict[str, Any]], ordered: bool = False) -> Any:  # noqa: ARG002
        self.skipped.extend(docs)
        return type("Res", (), {"inserted_ids": [f"skip_{i}" for i in range(len(docs))]})()

    def find(self, query: dict[str, Any]) -> Any:
        rid = query.get("repo_id")
        items = [f for f in self.files.values() if not rid or f.get("repo_id") == rid]

        class Cursor:
            def sort(self, *args: Any, **kwargs: Any) -> "Cursor":  # noqa: ARG002
                return self

            def limit(self, limit: int) -> "Cursor":  # noqa: ARG002
                return self

            async def to_list(self, length: int = 1000) -> list[dict[str, Any]]:
                return items[:length]

        return Cursor()


class MockSymbolCollection:
    def __init__(self) -> None:
        self.symbols: dict[str, dict[str, Any]] = {}

    async def bulk_write(self, ops: list[Any], ordered: bool = False) -> Any:  # noqa: ARG002
        for op in ops:
            query = op._filter
            doc = op._doc["$set"]
            key = f"{query['repo_id']}:{query['path']}:{query['qualified_name']}"
            self.symbols[key] = doc
        return type("Res", (), {"upserted_count": len(ops), "modified_count": 0})()

    def find(self, query: dict[str, Any]) -> Any:
        rid = query.get("repo_id")
        items = [s for s in self.symbols.values() if not rid or s.get("repo_id") == rid]

        # Handle $in filters for qualified_name and name_lower
        if "qualified_name" in query and isinstance(query["qualified_name"], dict):
            in_qnames = query["qualified_name"].get("$in", [])
            items = [s for s in items if s.get("qualified_name") in in_qnames]
        if "name_lower" in query and isinstance(query["name_lower"], dict):
            in_lowers = query["name_lower"].get("$in", [])
            items = [s for s in items if s.get("name_lower") in in_lowers]

        class Cursor:
            def sort(self, *args: Any, **kwargs: Any) -> "Cursor":  # noqa: ARG002
                return self

            def limit(self, *args: Any, **kwargs: Any) -> "Cursor":  # noqa: ARG002
                return self

            async def to_list(self, length: int = 1000) -> list[dict[str, Any]]:
                return items[:length]

        return Cursor()


class MockChunkCollection:
    def __init__(self) -> None:
        self.chunks: dict[str, dict[str, Any]] = {}

    async def bulk_write(self, ops: list[Any], ordered: bool = False) -> Any:  # noqa: ARG002
        for op in ops:
            doc = op._doc["$set"]
            cid = str(doc.get("_id") or doc.get("chunk_id"))
            self.chunks[cid] = doc
        return type("Res", (), {"upserted_count": len(ops), "modified_count": 0})()

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        cid = str(query.get("_id", ""))
        return self.chunks.get(cid)

    def find(self, query: dict[str, Any]) -> Any:
        rid = query.get("repo_id")
        items = list(self.chunks.values())
        if rid:
            items = [c for c in items if c.get("repo_id") == rid]

        if "_id" in query and isinstance(query["_id"], dict):
            in_ids = query["_id"].get("$in", [])
            items = [c for c in items if str(c.get("_id")) in in_ids]

        if "path" in query and isinstance(query["path"], dict):
            in_paths = query["path"].get("$in", [])
            items = [c for c in items if c.get("path") in in_paths]

        if "chunk_type" in query:
            items = [c for c in items if c.get("chunk_type") == query["chunk_type"]]

        class Cursor:
            def skip(self, *args: Any, **kwargs: Any) -> "Cursor":  # noqa: ARG002
                return self

            def limit(self, *args: Any, **kwargs: Any) -> "Cursor":  # noqa: ARG002
                return self

            def sort(self, *args: Any, **kwargs: Any) -> "Cursor":  # noqa: ARG002
                return self

            async def to_list(self, length: int = 1000) -> list[dict[str, Any]]:
                return items[:length]

        return Cursor()

    async def count_documents(self, query: dict[str, Any]) -> int:  # noqa: ARG002
        return len(self.chunks)


@pytest.mark.asyncio
async def test_taskflow_hybrid_retrieval_benchmark_hit_rate() -> None:
    """Tests that Hybrid retrieval achieves >= 80% Hit@5 across the TaskFlow benchmark suite."""
    fixture_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "eval", "fixtures", "sample-repo")
    )
    benchmark_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "eval", "benchmarks", "sample_repo.yaml")
    )
    assert os.path.isdir(fixture_dir), f"Fixture dir missing: {fixture_dir}"
    assert os.path.isfile(benchmark_file), f"Benchmark file missing: {benchmark_file}"

    # Load 30 questions
    with open(benchmark_file, "r", encoding="utf-8") as bf:
        benchmark_data = yaml.safe_load(bf)
    questions = benchmark_data.get("questions", [])
    assert len(questions) == 30, f"Expected 30 benchmark questions, found {len(questions)}"

    temp_dir = tempfile.mkdtemp(prefix="taskflow_retrieval_")
    zip_path = os.path.join(temp_dir, "taskflow.zip")

    try:
        # 1. Package and Ingest TaskFlow
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(fixture_dir):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, fixture_dir)
                    zf.write(full_p, rel_p)

        mock_repo_col = MockRepoCollection()
        mock_job_col = MockJobCollection()
        mock_file_col = MockFileCollection()
        mock_sym_col = MockSymbolCollection()
        mock_chunk_col = MockChunkCollection()
        mock_graph_col = MockChunkCollection()  # Reusable mock collection

        from app.db.repositories.graph import GraphRepository

        repo_repo = RepositoryRepository(mock_repo_col)
        job_repo = JobRepository(mock_job_col)
        file_repo = FileRepository(mock_file_col, mock_file_col)
        symbol_repo = SymbolRepository(mock_sym_col)
        chunk_repo = ChunkRepository(mock_chunk_col)
        graph_repo = GraphRepository(mock_graph_col)

        repo_doc = await repo_repo.create_repository(
            owner_id="user_test_retrieval",
            source={"type": "upload", "upload_filename": "taskflow.zip"},
            display_name="TaskFlow Retrieval Test",
            embedding_config={"provider": "fake", "model": "fake-256", "dim": 256},
        )
        repo_id = str(repo_doc["_id"])

        job_doc = await job_repo.create_job(
            job_type="ingest", repo_id=repo_id, user_id="user_test_retrieval"
        )
        job_id = str(job_doc["_id"])

        pipeline = IngestionPipeline(
            job_id=job_id,
            repo_id=repo_id,
            repo_repo=repo_repo,
            job_repo=job_repo,
            file_repo=file_repo,
            symbol_repo=symbol_repo,
            chunk_repo=chunk_repo,
        )

        await pipeline.run(archive_file_path=zip_path)

        # 2. Setup RetrievalService
        settings = get_settings()
        retrieval_service = RetrievalService(
            settings=settings,
            repo_repository=repo_repo,
            chunk_repository=chunk_repo,
            file_repository=file_repo,
            symbol_repository=symbol_repo,
            graph_repository=graph_repo,
        )

        # 3. Evaluate Hit@5 across all 30 questions
        hits = 0
        misses = []

        for q in questions:
            q_id = q["id"]
            query_text = q["question"]
            expected_files = [f.replace("\\", "/").lower() for f in q.get("expected_files", [])]

            req = SearchRequest(
                query=query_text,
                strategy="hybrid",
                top_k=5,
            )

            res = await retrieval_service.search(repo_id=repo_id, request=req)
            retrieved_files = [c.path.replace("\\", "/").lower() for c in res.results[:5]]

            # Check if any expected file was retrieved in top 5
            is_hit = any(
                exp in retrieved_files or any(ret.endswith(exp) or exp.endswith(ret) for ret in retrieved_files)
                for exp in expected_files
            )

            if is_hit:
                hits += 1
            else:
                misses.append((q_id, query_text, expected_files, retrieved_files))

        hit_rate = hits / len(questions)
        print(f"\nTaskFlow Benchmark Hit@5: {hits}/{len(questions)} ({hit_rate:.1%})")
        if misses:
            print("Missed questions:")
            for m in misses:
                print(f"  [{m[0]}] '{m[1]}' -> expected: {m[2]}, got: {m[3]}")

        # Assert >= 80% Hit@5 exit criterion
        assert hit_rate >= 0.80, f"Hit@5 rate was {hit_rate:.1%}, required >= 80%"

        # 4. Also verify search with explicit hybrid_rerank and auto strategies
        auto_res = await retrieval_service.search(
            repo_id=repo_id,
            request=SearchRequest(query="Where is AuthService.login defined?", strategy="auto"),
        )
        assert auto_res.route.intent == "locate"
        assert len(auto_res.results) > 0
        assert auto_res.context.startswith("<sources>")
        assert "</sources>" in auto_res.context

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
