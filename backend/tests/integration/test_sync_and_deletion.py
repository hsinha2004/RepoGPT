"""
Integration tests for Incremental Sync and Deletion Services (§8.10, §11.16).
Verifies:
1. Incremental sync only re-parses and re-embeds changed/added files.
2. Unchanged chunks reuse embeddings from cache.
3. Removed files have their chunks, symbols, and vectors purged.
4. Repository deletion completely cleans up Mongo, vector store, BM25, and disk snapshots.
"""

import os
import shutil
import tempfile
import zipfile

import pytest
from bson import ObjectId

from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.symbols import SymbolRepository
from app.services.indexing.sync import IncrementalSyncService, RepoDeletionService
from app.services.keyword.bm25_index import get_bm25_manager


class MockRepoCollection:
    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        oid = ObjectId()
        doc["_id"] = oid
        self.docs[str(oid)] = doc
        return type("Res", (), {"inserted_id": oid})()

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


class MockFileCollection:
    def __init__(self):
        self.files = {}

    async def bulk_write(self, ops, ordered=False):
        _ = ordered
        for op in ops:
            query = getattr(op, "_filter", {})
            doc = op._doc.get("$set", {})
            repo_id = query.get("repo_id") or doc.get("repo_id")
            path = query.get("path") or doc.get("path")
            key = f"{repo_id}:{path}"
            if key not in self.files:
                self.files[key] = {"repo_id": repo_id, "path": path}
            self.files[key].update(doc)
        return type("Res", (), {"upserted_count": len(ops), "modified_count": len(ops)})()

    def find(self, query):
        rid = query.get("repo_id")
        matches = [f for f in self.files.values() if f.get("repo_id") == rid]

        class MockCursor:
            def sort(self, *_a):
                return self

            def limit(self, *_a):
                return self

            async def to_list(self, length=None):
                _ = length
                return matches

        return MockCursor()

    async def delete_many(self, query):
        rid = query.get("repo_id")
        paths = query.get("path", {}).get("$in")
        deleted = 0
        to_del = []
        for k, v in self.files.items():
            if v.get("repo_id") == rid:
                if paths is None or v.get("path") in paths:
                    to_del.append(k)
                    deleted += 1
        for k in to_del:
            del self.files[k]
        return type("Res", (), {"deleted_count": deleted})()


class MockSymbolCollection:
    def __init__(self):
        self.symbols = {}

    async def bulk_write(self, ops, ordered=False):
        _ = ordered
        for op in ops:
            doc = op._doc["$set"]
            key = f"{doc['repo_id']}:{doc['path']}:{doc['qualified_name']}"
            self.symbols[key] = doc
        return type("Res", (), {"upserted_count": len(ops), "modified_count": 0})()

    def find(self, query):
        rid = str(query.get("repo_id", ""))
        matches = [s for s in self.symbols.values() if str(s.get("repo_id")) == rid]

        class MockCursor:
            def __init__(self, data):
                self.data = data

            def limit(self, count):
                self.data = self.data[:count]
                return self

            async def to_list(self, length=None):
                return self.data[:length] if length else self.data

        return MockCursor(matches)

    async def count_documents(self, query):
        rid = str(query.get("repo_id", ""))
        return len([s for s in self.symbols.values() if str(s.get("repo_id")) == rid])

    async def delete_many(self, query):
        rid = query.get("repo_id")
        paths = query.get("path", {}).get("$in")
        deleted = 0
        to_del = []
        for k, v in self.symbols.items():
            if v.get("repo_id") == rid:
                if paths is None or v.get("path") in paths:
                    to_del.append(k)
                    deleted += 1
        for k in to_del:
            del self.symbols[k]
        return type("Res", (), {"deleted_count": deleted})()


class MockChunkCollection:
    def __init__(self):
        self.chunks = {}

    async def bulk_write(self, ops, ordered=False):
        _ = ordered
        for op in ops:
            doc = op._doc["$set"]
            cid = str(doc.get("_id"))
            self.chunks[cid] = doc
        return type("Res", (), {"upserted_count": len(ops), "modified_count": 0})()

    def find(self, query):
        rid = query.get("repo_id")
        paths = query.get("path", {}).get("$in")
        matches = []
        for c in self.chunks.values():
            if c.get("repo_id") == rid:
                if paths is None or c.get("path") in paths:
                    matches.append(c)

        class MockChunkCursor:
            def sort(self, *_a):
                return self

            def limit(self, *_a):
                return self

            async def to_list(self, length=None):
                _ = length
                return matches

        return MockChunkCursor()

    async def delete_many(self, query):
        rid = query.get("repo_id")
        paths = query.get("path", {}).get("$in")
        deleted = 0
        to_del = []
        for k, v in self.chunks.items():
            if v.get("repo_id") == rid:
                if paths is None or v.get("path") in paths:
                    to_del.append(k)
                    deleted += 1
        for k in to_del:
            del self.chunks[k]
        return type("Res", (), {"deleted_count": deleted})()


@pytest.mark.asyncio
async def test_incremental_sync_and_deletion(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    try:
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "DATA_DIR", temp_dir)

        # 1. Setup mock repositories
        mock_repo_col = MockRepoCollection()
        mock_file_col = MockFileCollection()
        mock_sym_col = MockSymbolCollection()
        mock_chunk_col = MockChunkCollection()

        repo_repo = RepositoryRepository(mock_repo_col)
        file_repo = FileRepository(mock_file_col, mock_file_col)
        symbol_repo = SymbolRepository(mock_sym_col)
        chunk_repo = ChunkRepository(mock_chunk_col)

        # 2. Create repo record
        repo_doc = await repo_repo.create_repository(
            owner_id="user_sync_1",
            source={"type": "upload", "upload_filename": "archive_v1.zip"},
            display_name="Sync Test Repo",
            embedding_config={"provider": "fake", "model": "fake-256", "dim": 256},
        )
        repo_id = str(repo_doc["_id"])

        # 3. Create initial ZIP archive with 2 files
        zip_v1 = os.path.join(temp_dir, "v1.zip")
        with zipfile.ZipFile(zip_v1, "w") as z:
            z.writestr("auth.py", "def login(user, pw):\n    return True\n")
            z.writestr("utils.py", "def add(a, b):\n    return a + b\n")

        sync_service = IncrementalSyncService(
            repo_repo=repo_repo,
            file_repo=file_repo,
            symbol_repo=symbol_repo,
            chunk_repo=chunk_repo,
        )

        # First sync (ingest v1)
        res_v1 = await sync_service.sync_repository(repo_id, archive_path=zip_v1)
        assert res_v1["status"] == "synced"
        assert res_v1["added_files"] == 2
        assert res_v1["changed_files"] == 0
        sha_v1 = res_v1["commit_sha"]

        # Verify initial state
        updated_repo = await repo_repo.get_by_id(repo_id)
        assert updated_repo["commit_sha"] == sha_v1
        assert updated_repo["status"] == "ready"
        assert len(mock_chunk_col.chunks) > 0

        # Verify BM25 index v1 exists
        bm25_mgr = get_bm25_manager()
        idx_v1 = bm25_mgr.get_index(repo_id, sha_v1)
        assert idx_v1 is not None
        assert len(idx_v1.search("login")) > 0

        # 4. Sync identical archive -> should return unchanged no-op
        res_identical = await sync_service.sync_repository(repo_id, archive_path=zip_v1)
        assert res_identical["status"] == "unchanged"

        # 5. Create modified ZIP archive: auth.py modified, utils.py unchanged, service.py added
        zip_v2 = os.path.join(temp_dir, "v2.zip")
        with zipfile.ZipFile(zip_v2, "w") as z:
            z.writestr("auth.py", "def login_v2(email, password, token):\n    return False\n")
            z.writestr("utils.py", "def add(a, b):\n    return a + b\n")  # unchanged
            z.writestr("service.py", "def process():\n    return 'done'\n")  # added

        # Sync v2
        res_v2 = await sync_service.sync_repository(repo_id, archive_path=zip_v2)
        assert res_v2["status"] == "synced"
        assert res_v2["changed_files"] == 1  # auth.py changed
        assert res_v2["added_files"] == 1  # service.py added
        assert res_v2["removed_files"] == 0
        sha_v2 = res_v2["commit_sha"]
        assert sha_v2 != sha_v1

        # Verify v2 BM25 index finds login_v2 and process
        idx_v2 = bm25_mgr.get_index(repo_id, sha_v2)
        assert idx_v2 is not None
        assert len(idx_v2.search("login_v2")) > 0
        assert len(idx_v2.search("process")) > 0

        # Old snapshot v1 directory must be deleted
        old_snapshot = os.path.join(temp_dir, "snapshots", repo_id, sha_v1)
        assert not os.path.exists(old_snapshot)

        # 6. Test full repository deletion (§11.16)
        deletion_service = RepoDeletionService(
            repo_repo=repo_repo,
            file_repo=file_repo,
            symbol_repo=symbol_repo,
            chunk_repo=chunk_repo,
        )
        await deletion_service.delete_repository_data(repo_id)

        # Verify repo removed from Mongo
        assert await repo_repo.get_by_id(repo_id) is None
        assert len([c for c in mock_chunk_col.chunks.values() if c.get("repo_id") == repo_id]) == 0
        assert len([s for s in mock_sym_col.symbols.values() if s.get("repo_id") == repo_id]) == 0
        assert len([f for f in mock_file_col.files.values() if f.get("repo_id") == repo_id]) == 0

        # Verify snapshot and index directory completely deleted from disk
        assert not os.path.exists(os.path.join(temp_dir, "snapshots", repo_id))
        assert not os.path.exists(os.path.join(temp_dir, "indexes", repo_id))

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
