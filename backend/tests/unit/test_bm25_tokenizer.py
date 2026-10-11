"""
Unit tests for code-aware Tokenizer and BM25 index (§8.7).
"""

import os
import shutil
import tempfile

from app.services.keyword.bm25_index import BM25Index, BM25IndexManager
from app.services.keyword.tokenizer import split_subtokens, tokenize_code


def test_split_subtokens():
    # camelCase / PascalCase
    assert split_subtokens("getUserById") == ["get", "user", "by", "id"]
    assert split_subtokens("UserProfile") == ["user", "profile"]
    assert split_subtokens("XMLParser") == ["xml", "parser"]

    # snake_case / kebab-case
    assert split_subtokens("user_profile") == ["user", "profile"]
    assert split_subtokens("user-profile") == ["user", "profile"]
    assert split_subtokens("MAX_RETRIES_10") == ["max", "retries", "10"]

    # digits
    assert split_subtokens("HTTP2Client") == ["http", "2", "client"]


def test_tokenize_code_comprehensive():
    # 1. camelCase, snake_case, kebab-case: compound kept AND subtokens present
    tokens = tokenize_code("const userProfile = getUserById(user_id);")
    # Compounds
    assert "userprofile" in tokens
    assert "getuserbyid" in tokens
    assert "user_id" in tokens
    # Subtokens
    assert "user" in tokens
    assert "profile" in tokens
    assert "get" in tokens
    assert "id" in tokens

    # 2. Stop words are dropped
    assert "const" not in tokens
    assert "def" not in tokens

    # 3. Tokens < 2 characters are dropped
    single_char_tokens = [t for t in tokens if len(t) < 2]
    assert len(single_char_tokens) == 0


def test_tokenize_code_path_boost():
    # Path boost: path segments added twice
    text = "def authenticate(): pass"
    path = "backend/app/auth/login_service.py"
    tokens = tokenize_code(text, file_path=path)

    # Count occurrences of path segments
    # 'auth' appears 2 times from path
    assert tokens.count("auth") == 2
    # 'backend' appears 2 times from path
    assert tokens.count("backend") == 2
    # 'login' appears 2 times from path subtokens
    assert tokens.count("login") >= 2


def test_tokenize_code_path_from_header():
    # Detects path from 'File: <path>' header if file_path is None
    header_text = "File: src/components/UserProfile.tsx (typescript)\nconst Card = () => null;"
    tokens = tokenize_code(header_text)
    assert tokens.count("components") >= 2


def test_bm25_index_build_and_search():
    temp_dir = tempfile.mkdtemp()
    try:
        chunks = [
            {
                "id": "c1",
                "embed_text": "File: auth/login.py\ndef login(email, password):\n    return auth_service.verify(email, password)",
                "file_path": "auth/login.py",
            },
            {
                "id": "c2",
                "embed_text": "File: tasks/service.py\ndef create_task(title, description):\n    return db.tasks.insert(title)",
                "file_path": "tasks/service.py",
            },
            {
                "id": "c3",
                "embed_text": "File: users/controller.py\ndef getUserById(user_id):\n    return user_repo.find_one(user_id)",
                "file_path": "users/controller.py",
            },
        ]

        # 1. Build index
        index = BM25Index.build(chunks, temp_dir)
        assert len(index.chunk_ids) == 3

        # 2. Search for login
        res_login = index.search("login", k=5)
        assert len(res_login) > 0
        assert res_login[0].chunk_id == "c1"
        assert res_login[0].score > 0.0
        assert res_login[0].rank == 1

        # 3. Search for user by ID (camelCase query)
        res_user = index.search("getUserById", k=5)
        assert len(res_user) > 0
        assert res_user[0].chunk_id == "c3"

        # 4. Persistence: load from disk
        loaded = BM25Index.load(temp_dir)
        assert len(loaded.chunk_ids) == 3
        res_loaded = loaded.search("create_task", k=5)
        assert len(res_loaded) > 0
        assert res_loaded[0].chunk_id == "c2"

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_bm25_manager_lru_and_cleanup(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    try:
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "DATA_DIR", temp_dir)

        manager = BM25IndexManager(maxsize=2)
        repo_id = "test_repo_mgr"

        chunks = [{"id": "c1", "embed_text": "hello world", "file_path": "main.py"}]

        # Build commit 1
        idx_dir_1 = manager.get_index_dir(repo_id, "sha1")
        idx1 = BM25Index.build(chunks, idx_dir_1)
        manager.put_index(repo_id, "sha1", idx1)

        # Build commit 2
        idx_dir_2 = manager.get_index_dir(repo_id, "sha2")
        idx2 = BM25Index.build(chunks, idx_dir_2)
        manager.put_index(repo_id, "sha2", idx2)

        # Both present
        assert manager.get_index(repo_id, "sha1") is not None
        assert manager.get_index(repo_id, "sha2") is not None

        # Build commit 3 -> evicts sha1 from LRU cache
        idx_dir_3 = manager.get_index_dir(repo_id, "sha3")
        idx3 = BM25Index.build(chunks, idx_dir_3)
        manager.put_index(repo_id, "sha3", idx3)

        # sha1 was evicted from in-memory cache, but reloads from disk on demand!
        reloaded_sha1 = manager.get_index(repo_id, "sha1")
        assert reloaded_sha1 is not None

        # Evict & delete
        manager.delete_index(repo_id, "sha1")
        assert not idx_dir_1.exists()

        # Delete entire repo index
        manager.delete_index(repo_id)
        assert not (manager.get_index_dir(repo_id, "sha2")).parent.exists()

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
