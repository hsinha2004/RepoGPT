"""
Database seeding script for initial setup (§16.4).
Creates default administrator account and verifies built-in benchmarks.
"""

from __future__ import annotations

import asyncio
import sys

from app.core.security import hash_password
from app.db.mongo import get_database
from app.db.repositories.benchmarks import BenchmarkRepository
from app.db.repositories.users import UserRepository


async def seed() -> None:
    print("Seeding RepoGPT database...")

    # 1. Connect to MongoDB
    try:
        db = get_database()
        _ = await db.command("ping")
        print("MongoDB connection verified.")
    except Exception as exc:
        print(f"Warning: Could not connect to MongoDB: {exc}", file=sys.stderr)
        return

    # 2. Seed Administrator Account
    user_repo = UserRepository()
    admin_email = "admin@repogpt.local"
    existing_admin = await user_repo.get_by_email(admin_email)

    if not existing_admin:
        admin_pass = "AdminPassword123!"
        hashed = hash_password(admin_pass)
        created = await user_repo.create_user(
            email=admin_email,
            name="RepoGPT Administrator",
            password_hash=hashed,
            role="admin",
        )
        print(f"Admin account created successfully: {admin_email} (ID: {created['_id']})")
        print(f"Default credentials: Email: {admin_email} | Password: {admin_pass}")
    else:
        print(f"Admin account already exists: {admin_email} (Role: {existing_admin.get('role')})")

    # 3. Verify Built-in Evaluation Benchmarks
    b_repo = BenchmarkRepository()
    benchmarks = await b_repo.list_benchmarks()
    print(f"Available benchmarks ({len(benchmarks)}):")
    for b in benchmarks:
        print(f" - [{b.get('id')}] {b.get('name')} ({b.get('question_count', 0)} questions)")

    print("Seeding completed successfully.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
