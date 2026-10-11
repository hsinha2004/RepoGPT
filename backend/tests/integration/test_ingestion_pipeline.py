"""
Integration test for repository ingestion pipeline (§8.1 & §8.2 & §14.4).
Tests safe extraction, filtering, classification, and stats updates on the TaskFlow fixture repo.
"""

import os
import shutil
import tempfile
import zipfile

import pytest
from bson import ObjectId

from app.db.repositories.files import FileRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.repos import RepositoryRepository
from app.services.ingestion.pipeline import IngestionPipeline


class MockRepoCollection:
    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        oid = ObjectId()
        doc["_id"] = oid
        self.docs[str(oid)] = doc

        class Result:
            inserted_id = oid

        return Result()

    async def find_one(self, query):
        oid = str(query.get("_id", ""))
        return self.docs.get(oid)

    async def update_one(self, query, update):
        oid = str(query.get("_id", ""))
        doc = self.docs.get(oid)
        if not doc:
            return type("Res", (), {"modified_count": 0})()
        if "$set" in update:
            doc.update(update["$set"])
        return type("Res", (), {"modified_count": 1})()

    async def delete_one(self, query):
        oid = str(query.get("_id", ""))
        if oid in self.docs:
            del self.docs[oid]
            return type("Res", (), {"deleted_count": 1})()
        return type("Res", (), {"deleted_count": 0})()


class MockJobCollection:
    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        oid = ObjectId()
        doc["_id"] = oid
        self.docs[str(oid)] = doc

        class Result:
            inserted_id = oid

        return Result()

    async def find_one(self, query):
        oid = str(query.get("_id", ""))
        return self.docs.get(oid)

    async def update_one(self, query, update):
        oid = str(query.get("_id", ""))
        doc = self.docs.get(oid)
        if not doc:
            return type("Res", (), {"modified_count": 0})()
        if "$set" in update:
            doc.update(update["$set"])
        if "$push" in update:
            for k, v in update["$push"].items():
                if "$each" in v:
                    doc.setdefault(k, []).extend(v["$each"])
        return type("Res", (), {"modified_count": 1})()


class MockFileCollection:
    def __init__(self):
        self.files = {}
        self.skipped = []

    async def bulk_write(self, ops, ordered: bool = False):
        _ = ordered
        for op in ops:
            query = op._filter
            doc = op._doc["$set"]
            key = f"{query['repo_id']}:{query['path']}"
            self.files[key] = doc
        return type("Res", (), {"upserted_count": len(ops), "modified_count": 0})()

    async def insert_many(self, docs, ordered: bool = False):
        _ = ordered
        self.skipped.extend(docs)
        return type("Res", (), {"inserted_ids": [f"skip_{i}" for i in range(len(docs))]})()


@pytest.mark.asyncio
async def test_taskflow_fixture_ingestion_pipeline():
    # 1. Package TaskFlow fixture into a temporary ZIP archive
    fixture_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "eval", "fixtures", "sample-repo")
    )
    assert os.path.isdir(fixture_dir), f"TaskFlow fixture directory missing at {fixture_dir}"

    temp_dir = tempfile.mkdtemp(prefix="taskflow_test_")
    zip_path = os.path.join(temp_dir, "taskflow.zip")

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(fixture_dir):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, fixture_dir)
                    zf.write(full_p, rel_p)

        # 2. Setup mock repositories
        mock_repo_col = MockRepoCollection()
        mock_job_col = MockJobCollection()
        mock_file_col = MockFileCollection()

        repo_repo = RepositoryRepository(mock_repo_col)
        job_repo = JobRepository(mock_job_col)
        file_repo = FileRepository(mock_file_col, mock_file_col)

        # Seed repository and job
        repo_doc = await repo_repo.create_repository(
            owner_id="user_test_1",
            source={"type": "upload", "upload_filename": "taskflow.zip"},
            display_name="TaskFlow Sample",
        )
        repo_id = str(repo_doc["_id"])

        job_doc = await job_repo.create_job(
            job_type="ingest", repo_id=repo_id, user_id="user_test_1"
        )
        job_id = str(job_doc["_id"])

        # 3. Run IngestionPipeline
        pipeline = IngestionPipeline(
            job_id=job_id,
            repo_id=repo_id,
            repo_repo=repo_repo,
            job_repo=job_repo,
            file_repo=file_repo,
        )

        result = await pipeline.run(archive_file_path=zip_path)

        # 4. Verify pipeline results
        assert result["repo_id"] == repo_id
        assert result["files_count"] >= 30
        assert result["loc"] > 200

        # Verify repo status and stats
        updated_repo = await repo_repo.get_by_id(repo_id)
        assert updated_repo["status"] == "ready"
        stats = updated_repo["stats"]
        assert stats["files_indexed"] >= 30
        assert "python" in stats["languages"]
        assert "typescript" in stats["languages"]
        assert "go" in stats["languages"]
        assert "java" in stats["languages"]

        # Verify job finished as succeeded
        updated_job = await job_repo.get_by_id(job_id)
        assert updated_job["status"] == "succeeded"
        assert updated_job["progress"] == 100

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
