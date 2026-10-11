#!/usr/bin/env python3
"""
Generate secrets and populate .env from .env.example
"""
import base64
import os
import re
import secrets
import sys
from pathlib import Path


def generate_fernet_key() -> str:
    """Generate a standard URL-safe base64-encoded 32-byte key compatible with Fernet."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")


def generate_jwt_secret() -> str:
    """Generate a >= 64-byte urlsafe secret for JWT signing."""
    return base64.urlsafe_b64encode(secrets.token_bytes(64)).decode("utf-8").rstrip("=")


def main():
    root_dir = Path(__file__).resolve().parent.parent
    env_example = root_dir / ".env.example"
    env_file = root_dir / ".env"

    if not env_example.exists():
        print(f"Error: {env_example} does not exist.", file=sys.stderr)
        sys.exit(1)

    if env_file.exists():
        print(f".env already exists at {env_file}. Preserving existing file.")
        return

    content = env_example.read_text(encoding="utf-8")

    generated_secrets = {
        "JWT_SECRET": generate_jwt_secret(),
        "ENCRYPTION_KEY": generate_fernet_key(),
        "ADMIN_PASSWORD": secrets.token_urlsafe(18),
        "MONGO_ROOT_PASSWORD": secrets.token_urlsafe(24),
        "MONGO_APP_PASSWORD": secrets.token_urlsafe(24),
        "REDIS_PASSWORD": secrets.token_urlsafe(24),
        "GITHUB_WEBHOOK_SECRET": secrets.token_hex(20),
    }

    for key, val in generated_secrets.items():
        pattern = rf"^({key}=).*$"
        content = re.sub(pattern, rf"\g<1>{val}", content, flags=re.MULTILINE)

    env_file.write_text(content, encoding="utf-8")
    print(f"Successfully created {env_file} with cryptographically generated secrets.")
    print("----------------------------------------------------------------------")
    print(f"Generated Admin Email   : admin@repogpt.local")
    print(f"Generated Admin Password: {generated_secrets['ADMIN_PASSWORD']}")
    print("----------------------------------------------------------------------")


if __name__ == "__main__":
    main()
