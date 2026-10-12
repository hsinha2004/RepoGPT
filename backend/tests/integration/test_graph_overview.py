"""
Integration tests for dependency graph, architecture analysis, and onboarding overview (§8.8, §8.9, §12).
"""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from typing import Any

import pytest
from bson import ObjectId

from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository
from app.db.repositories.graph import GraphRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.overview import OverviewRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.symbols import SymbolRepository
from app.services.ingestion.pipeline import IngestionPipeline


class MockCollection:
    def __init__(self):
        self.docs: dict[str, dict[str, Any]] = {}

    async def insert_one(self, doc: dict[str, Any]):
        oid = ObjectId()
        doc["_id"] = oid
        self.docs[str(oid)] = doc

        class Res:
            inserted_id = oid

        return Res()

    async def find_one(self, query: dict[str, Any]):
        if "_id" in query:
            return self.docs.get(str(query["_id"]))
        if "repo_id" in query:
            for d in self.docs.values():
                if str(d.get("repo_id")) == str(query["repo_id"]):
                    return d
        return None

    def find(self, query: dict[str, Any]):
        results = []
        for d in self.docs.values():
            match = True
            for k, v in query.items():
                if k == "$or":
                    # Simple OR match
                    sub_match = any(
                        d.get("source") in cond.get("source", {}).get("$in", [])
                        or d.get("target") in cond.get("target", {}).get("$in", [])
                        for cond in v
                    )
                    if not sub_match:
                        match = False
                        break
                elif str(d.get(k)) != str(v):
                    match = False
                    break
            if match:
                results.append(dict(d))

        class Cursor:
            def __init__(self, data):
                self.data = data

            def limit(self, count):
                self.data = self.data[:count]
                return self

            async def to_list(self, length=1000):
                return self.data[:length]

        return Cursor(results)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]):
        doc = await self.find_one(query)
        if doc and "$set" in update:
            doc.update(update["$set"])
            return type("Res", (), {"modified_count": 1})()
        return type("Res", (), {"modified_count": 0})()

    async def find_one_and_update(
        self, query: dict[str, Any], update: dict[str, Any], upsert=False, return_document=True
    ):
        _ = return_document
        doc = await self.find_one(query)
        if not doc and upsert:
            doc = dict(query)
            if "$setOnInsert" in update:
                doc.update(update["$setOnInsert"])
            if "$set" in update:
                doc.update(update["$set"])
            oid = ObjectId()
            doc["_id"] = oid
            self.docs[str(oid)] = doc
            return doc
        elif doc and "$set" in update:
            doc.update(update["$set"])
            return doc
        return doc

    async def bulk_write(self, ops, ordered=False):
        _ = ordered
        upserted = 0
        for op in ops:
            query = op._filter
            update = op._doc
            upsert = op._upsert
            await self.find_one_and_update(query, update, upsert=upsert)
            upserted += 1
        return type("Res", (), {"upserted_count": upserted, "modified_count": 0})()

    async def delete_many(self, query: dict[str, Any]):
        to_del = [
            k for k, d in self.docs.items() if str(d.get("repo_id")) == str(query.get("repo_id"))
        ]
        for k in to_del:
            del self.docs[k]
        return type("Res", (), {"deleted_count": len(to_del)})()

    async def count_documents(self, query: dict[str, Any]):
        return len(
            [d for d in self.docs.values() if str(d.get("repo_id")) == str(query.get("repo_id"))]
        )


@pytest.mark.asyncio
async def test_pipeline_graph_and_overview_stages():
    """Verify that IngestionPipeline executes Stage 9 (graph) and Stage 10 (overview)."""
    fixtures_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "eval", "fixtures", "sample-repo")
    )
    assert os.path.isdir(fixtures_dir), f"TaskFlow fixture missing at {fixtures_dir}"
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "taskflow.zip")

    try:
        # Create archive of TaskFlow fixture
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(fixtures_dir):
                for f in files:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, fixtures_dir)
                    zf.write(full, rel)

        # Mock database collections
        mock_repo_col = MockCollection()
        mock_job_col = MockCollection()
        mock_file_col = MockCollection()
        mock_sym_col = MockCollection()
        mock_chunk_col = MockCollection()
        mock_graph_col = MockCollection()
        mock_overview_col = MockCollection()

        repo_repo = RepositoryRepository(mock_repo_col)
        job_repo = JobRepository(mock_job_col)
        file_repo = FileRepository(mock_file_col, mock_file_col)
        symbol_repo = SymbolRepository(mock_sym_col)
        chunk_repo = ChunkRepository(mock_chunk_col)
        graph_repo = GraphRepository(mock_graph_col)
        overview_repo = OverviewRepository(mock_overview_col)

        # Seed repo & job
        repo_doc = await repo_repo.create_repository(
            owner_id="user_graph_test",
            source={"type": "upload", "upload_filename": "taskflow.zip"},
            display_name="TaskFlow Graph Test",
            embedding_config={"provider": "fake", "model": "fake-256", "dim": 256},
        )
        repo_id = str(repo_doc["_id"])

        job_doc = await job_repo.create_job(
            job_type="ingest", repo_id=repo_id, user_id="user_graph_test"
        )
        job_id = str(job_doc["_id"])

        # Execute IngestionPipeline (All 10 Stages)
        pipeline = IngestionPipeline(
            job_id=job_id,
            repo_id=repo_id,
            repo_repo=repo_repo,
            job_repo=job_repo,
            file_repo=file_repo,
            symbol_repo=symbol_repo,
            chunk_repo=chunk_repo,
            graph_repo=graph_repo,
            overview_repo=overview_repo,
        )

        result = await pipeline.run(archive_file_path=zip_path)
        assert result["repo_id"] == repo_id
        assert result["files_count"] >= 30

        # 1. Assert Stage 9 (Graph) results
        edges = await graph_repo.list_for_repo(repo_id)
        assert len(edges) > 0, "Graph edges must be constructed and persisted"
        # Check that import and call edges exist
        edge_types = {e.get("type") for e in edges}
        assert "imports" in edge_types

        # 2. Assert Stage 10 (Overview) results
        overview_doc = await overview_repo.get_by_repo(repo_id)
        assert overview_doc is not None, "Repo overview document must be persisted"
        assert len(overview_doc.get("markdown", "")) > 50
        assert len(overview_doc.get("suggested_questions", [])) >= 5
        assert len(overview_doc.get("tech_stack", [])) > 0
        assert len(overview_doc.get("entry_points", [])) > 0
        assert len(overview_doc.get("reading_order", [])) >= 5

        # Check citations exist in overview
        sources = overview_doc.get("sources", [])
        assert len(sources) > 0, "Sources must be numbered for citations"
        assert sources[0]["id"] == "S1"

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
