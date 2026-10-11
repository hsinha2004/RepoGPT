"""
Unit tests for VectorStore implementations (Chroma and FAISS) (§6.3).
"""

import os
import shutil
import tempfile

from app.services.indexing.vector.chroma import ChromaVectorStore
from app.services.indexing.vector.faiss_store import FAISSVectorStore


def test_chroma_vector_store_operations():
    # Test Chroma collection creation, upsert, query, delete, drop
    repo_id = "test_repo_chroma"
    model_slug = "fake_256"

    store = ChromaVectorStore(repo_id=repo_id, model_slug=model_slug)
    try:
        # Start clean
        store.drop()
        assert store.count() == 0

        # Upsert vectors
        ids = ["c1", "c2", "c3"]
        vectors = [
            [1.0, 0.0, 0.0, 0.0] + [0.0] * 252,
            [0.0, 1.0, 0.0, 0.0] + [0.0] * 252,
            [0.0, 0.0, 1.0, 0.0] + [0.0] * 252,
        ]
        metadatas = [
            {"path": "auth/login.py", "chunk_type": "code"},
            {"path": "auth/user.py", "chunk_type": "code"},
            {"path": "models/task.py", "chunk_type": "code"},
        ]

        store.upsert(ids=ids, vectors=vectors, metadatas=metadatas)
        assert store.count() == 3

        # Query for vector closest to c1
        q_vec = [0.99, 0.01, 0.0, 0.0] + [0.0] * 252
        matches = store.query(vector=q_vec, k=2)
        assert len(matches) > 0
        assert matches[0].id == "c1"
        assert matches[0].score > 0.9  # high cosine similarity

        # Delete c2
        store.delete(["c2"])
        assert store.count() == 2

        # Verify c2 is gone
        m2 = store.query(vector=[0.0, 1.0, 0.0, 0.0] + [0.0] * 252, k=1)
        if m2:
            assert m2[0].id != "c2"

    finally:
        store.drop()


def test_faiss_vector_store_operations(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    try:
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "DATA_DIR", temp_dir)

        repo_id = "test_repo_faiss"
        model_slug = "fake_256"

        store = FAISSVectorStore(repo_id=repo_id, model_slug=model_slug, dim=256)
        assert store.count() == 0

        ids = ["f1", "f2", "f3"]
        vectors = [
            [1.0, 0.0, 0.0, 0.0] + [0.0] * 252,
            [0.0, 1.0, 0.0, 0.0] + [0.0] * 252,
            [0.0, 0.0, 1.0, 0.0] + [0.0] * 252,
        ]
        metadatas = [
            {"path": "main.py", "chunk_type": "code"},
            {"path": "utils.py", "chunk_type": "code"},
            {"path": "test.py", "chunk_type": "test"},
        ]

        store.upsert(ids=ids, vectors=vectors, metadatas=metadatas)
        assert store.count() == 3

        # Query top match
        q_vec = [1.0, 0.0, 0.0, 0.0] + [0.0] * 252
        matches = store.query(vector=q_vec, k=2)
        assert len(matches) > 0
        assert matches[0].id == "f1"
        assert matches[0].score > 0.95

        # Query with metadata filter
        filtered = store.query(vector=q_vec, k=5, where={"chunk_type": "test"})
        assert len(filtered) == 1
        assert filtered[0].id == "f3"

        # Persistence verification: reload new store from same disk path
        store2 = FAISSVectorStore(repo_id=repo_id, model_slug=model_slug, dim=256)
        assert store2.count() == 3
        m_reload = store2.query(vector=q_vec, k=1)
        assert m_reload[0].id == "f1"

        # Delete item
        store2.delete(["f1"])
        assert store2.count() == 2

        store2.drop()
        assert store2.count() == 0

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
