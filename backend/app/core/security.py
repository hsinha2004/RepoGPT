"""
Security, Cryptography, Password Hashing (Argon2id), JWT, and Token Utilities.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.errors import UnauthorizedError, ValidationFailedError

# Common weak passwords list for validation
COMMON_PASSWORDS = {
    "password",
    "12345678",
    "123456789",
    "1234567890",
    "qwertyuiop",
    "password123",
    "admin123",
    "letmein123",
    "welcome123",
    "iloveyou1",
    "changeme123",
    "testing123",
    "repogpt123",
}

ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, bool]:
    """
    Verify password. Returns (is_valid, needs_rehash).
    """
    try:
        is_valid = ph.verify(hashed_password, plain_password)
        needs_rehash = ph.check_needs_rehash(hashed_password)
        return is_valid, needs_rehash
    except VerifyMismatchError:
        return False, False
    except Exception:
        return False, False


def validate_password_strength(password: str, email: str) -> None:
    """
    Validate password requirements:
    10-128 chars, not in common passwords, not equal to email.
    """
    if len(password) < 10 or len(password) > 128:
        raise ValidationFailedError("Password must be between 10 and 128 characters long")
    if password.lower() == email.lower():
        raise ValidationFailedError("Password cannot be identical to email address")
    if password.lower() in COMMON_PASSWORDS:
        raise ValidationFailedError("Password is too common; choose a stronger password")


def hash_token(token: str) -> str:
    """Compute SHA-256 hex digest of an opaque token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_opaque_token(nbytes: int = 32) -> str:
    """Generate a high-entropy URL-safe opaque token."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(user_id: str, role: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    exp = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES))
    payload = {
        "sub": user_id,
        "role": role,
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
        "iss": "repogpt",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    if not token or not token.strip() or token.strip() in ("null", "undefined"):
        raise UnauthorizedError("Missing or invalid access token")
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            issuer="repogpt",
            options={"require": ["sub", "role", "exp", "type"]},
        )
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Access token has expired") from None
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError(f"Invalid access token: {str(e)}") from e


def get_fernet_cipher() -> Fernet:
    settings = get_settings()
    key = settings.ENCRYPTION_KEY.encode("utf-8")
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string (e.g. GitHub PAT) using Fernet."""
    if not plaintext:
        return ""
    cipher = get_fernet_cipher()
    return cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a secret string using Fernet."""
    if not ciphertext:
        return ""
    cipher = get_fernet_cipher()
    return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def constant_time_compare(val1: str, val2: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return secrets.compare_digest(val1, val2)
