import pytest

from app.core.errors import ValidationFailedError
from app.core.security import (
    constant_time_compare,
    create_access_token,
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
    generate_opaque_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)


def test_password_hashing_and_verification():
    password = "StrongPassword123!"
    hashed = hash_password(password)
    assert hashed.startswith("$argon2id$")

    is_valid, _ = verify_password(password, hashed)
    assert is_valid is True

    is_wrong, _ = verify_password("WrongPassword123!", hashed)
    assert is_wrong is False


def test_password_strength_validation():
    # Too short (< 10)
    with pytest.raises(ValidationFailedError):
        validate_password_strength("short123", "user@example.com")

    # Identical to email
    with pytest.raises(ValidationFailedError):
        validate_password_strength("user@example.com", "user@example.com")

    # Common password
    with pytest.raises(ValidationFailedError):
        validate_password_strength("password123", "user@example.com")

    # Valid password
    validate_password_strength("ValidSecurePassword2026!", "user@example.com")


def test_jwt_access_token_lifecycle():
    user_id = "507f1f77bcf86cd799439011"
    role = "user"
    token = create_access_token(user_id=user_id, role=role)
    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert payload["type"] == "access"
    assert payload["iss"] == "repogpt"


def test_opaque_token_and_hashing():
    token = generate_opaque_token(32)
    h1 = hash_token(token)
    h2 = hash_token(token)
    assert h1 == h2
    assert len(h1) == 64


def test_fernet_secret_encryption():
    secret = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret


def test_constant_time_compare():
    assert constant_time_compare("exact_match", "exact_match") is True
    assert constant_time_compare("exact_match", "mismatch") is False
