import pytest
from app.auth.security import hash_password, verify_password, create_access_token, decode_token


def test_password_hashing():
    pw = "SecretPassword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_token_creation_and_decoding():
    payload = {"sub": "developer@taskflow.dev", "uid": 42}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "developer@taskflow.dev"
    assert decoded["uid"] == 42
    assert "exp" in decoded
