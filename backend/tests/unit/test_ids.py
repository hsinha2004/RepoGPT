from app.core.ids import generate_chunk_id, generate_object_id, is_valid_object_id


def test_object_id_validation():
    oid = generate_object_id()
    assert is_valid_object_id(oid) is True
    assert len(oid) == 24
    assert is_valid_object_id("invalid-id") is False
    assert is_valid_object_id("507f1f77bcf86cd799439011") is True


def test_deterministic_chunk_id():
    repo_id = "507f1f77bcf86cd799439011"
    path = "backend/app/auth/security.py"
    start_line = 10
    end_line = 45
    content_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    cid1 = generate_chunk_id(repo_id, path, start_line, end_line, content_hash)
    cid2 = generate_chunk_id(repo_id, path, start_line, end_line, content_hash)

    assert cid1 == cid2
    assert len(cid1) == 24

    # Different line produces different chunk ID
    cid3 = generate_chunk_id(repo_id, path, start_line + 1, end_line, content_hash)
    assert cid1 != cid3
