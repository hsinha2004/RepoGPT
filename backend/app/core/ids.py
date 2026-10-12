"""
ID generation and conversion utilities.
"""

import hashlib
import re

from bson import ObjectId

OBJECT_ID_REGEX = re.compile(r"^[0-9a-fA-F]{24}$")


def is_valid_object_id(val: str) -> bool:
    """Validate if a string is a 24-character hexadecimal ObjectId."""
    return bool(OBJECT_ID_REGEX.match(val))


def generate_object_id() -> str:
    """Generate a new random 24-character hex ObjectId string."""
    return str(ObjectId())


def to_object_id(val: str | ObjectId) -> ObjectId:
    """Converts a 24-char hex string to BSON ObjectId."""
    if isinstance(val, ObjectId):
        return val
    str_val = str(val)
    if not is_valid_object_id(str_val):
        from app.core.errors import ValidationFailedError

        raise ValidationFailedError(f"Invalid ObjectId hex format: '{val}'")
    return ObjectId(str_val)


def generate_chunk_id(
    repo_id: str, path: str, start_line: int, end_line: int, content_hash: str
) -> str:
    """
    Deterministic chunk ID as per §6.1:
    sha1(repo_id + path + start_line + end_line + content_hash)[:24]
    """
    payload = f"{repo_id}:{path}:{start_line}:{end_line}:{content_hash}".encode()
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()[:24]
