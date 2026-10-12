"""
MongoDB repository for the reviews collection (§6.2, §10, §12.6).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection


class ReviewRepository:
    """MongoDB repository for the reviews collection."""

    def __init__(self, collection: Any | None = None) -> None:
        self._col_raw = collection

    @property
    def _col(self) -> Any:
        if self._col_raw is not None:
            return self._col_raw
        return get_collection("reviews")

    async def create_review(
        self,
        repo_id: str,
        user_id: str,
        source: dict[str, Any],
        indexed_commit_mismatch: bool = False,
    ) -> dict[str, Any]:
        """Creates a pending review record."""
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "repo_id": repo_id,
            "user_id": user_id,
            "source": source,
            "status": "pending",
            "risk_level": "low",
            "stats": {
                "files_changed": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "findings_count": 0,
                "accepted_count": 0,
                "rejected_count": 0,
            },
            "summary": "",
            "file_walkthrough": [],
            "findings": [],
            "general_comments": [],
            "published_to_github": False,
            "github_review_id": None,
            "github_review_url": None,
            "error": None,
            "indexed_commit_mismatch": indexed_commit_mismatch,
            "created_at": now,
            "updated_at": now,
        }
        res = await self._col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def get_by_id(self, review_id: str) -> dict[str, Any] | None:
        """Fetch review document by ID."""
        try:
            return await self._col.find_one({"_id": ObjectId(review_id)})
        except Exception:
            return await self._col.find_one({"_id": review_id})

    async def list_for_repo(self, repo_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """List reviews for a repository ordered by most recent."""
        cursor = self._col.find({"repo_id": str(repo_id)}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def update_results(
        self,
        review_id: str,
        status: str,
        risk_level: str,
        stats: dict[str, Any],
        summary: str,
        file_walkthrough: list[dict[str, Any]],
        findings: list[dict[str, Any]],
        general_comments: list[dict[str, Any]],
        error: str | None = None,
    ) -> dict[str, Any] | None:
        """Update review document with generated review findings."""
        now = datetime.now(UTC)
        oid = ObjectId(review_id) if ObjectId.is_valid(review_id) else review_id
        await self._col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": status,
                    "risk_level": risk_level,
                    "stats": stats,
                    "summary": summary,
                    "file_walkthrough": file_walkthrough,
                    "findings": findings,
                    "general_comments": general_comments,
                    "error": error,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(review_id)

    async def update_finding(
        self,
        review_id: str,
        finding_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update a specific finding's status, severity, title, or note."""
        doc = await self.get_by_id(review_id)
        if not doc:
            return None

        findings = doc.get("findings", [])
        finding_found = False
        accepted_count = 0
        rejected_count = 0

        for f in findings:
            if f.get("id") == finding_id:
                for k, v in updates.items():
                    if v is not None:
                        f[k] = v
                finding_found = True

            status = f.get("status", "pending")
            if status in {"accepted", "edited"}:
                accepted_count += 1
            elif status == "rejected":
                rejected_count += 1

        if not finding_found:
            return None

        stats = doc.get("stats", {})
        stats["accepted_count"] = accepted_count
        stats["rejected_count"] = rejected_count

        now = datetime.now(UTC)
        oid = ObjectId(review_id) if ObjectId.is_valid(review_id) else review_id
        await self._col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "findings": findings,
                    "stats": stats,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(review_id)

    async def mark_published(
        self,
        review_id: str,
        github_review_id: str,
        github_review_url: str,
    ) -> dict[str, Any] | None:
        """Mark review as published to GitHub."""
        now = datetime.now(UTC)
        oid = ObjectId(review_id) if ObjectId.is_valid(review_id) else review_id
        await self._col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "published_to_github": True,
                    "github_review_id": github_review_id,
                    "github_review_url": github_review_url,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(review_id)
