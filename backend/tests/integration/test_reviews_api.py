"""
Integration tests for PR Review API lifecycle (§10, §12.6).
Tests diff upload, PR URL review, findings curation, GitHub publishing (mocked),
Markdown/JSON export, and evaluation metrics across seeded patches.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

import app.db.mongo as mongo
from app.core.config import Settings
from app.core.deps import get_current_user
from app.db.repositories.files import FileRepository
from app.main import create_app

SAMPLE_DIFF = """--- a/app/tasks.py
+++ b/app/tasks.py
@@ -10,3 +10,4 @@
 def list_user_tasks(user_id: int):
-    return db.query(user_id)
+    query = f"SELECT * FROM tasks WHERE user_id = '{user_id}'"
+    return db.execute(query)
"""


class MockReviewsDatabase:
    def __init__(self) -> None:
        self.reviews: dict[str, dict[str, Any]] = {}
        self.repos: dict[str, dict[str, Any]] = {}

    def get_collection(self, name: str) -> Any:
        return MockReviewsCollection(self, name)

    def __getattr__(self, name: str) -> Any:
        return self.get_collection(name)

    def __getitem__(self, name: str) -> Any:
        return self.get_collection(name)


class MockReviewsCollection:
    def __init__(self, db: MockReviewsDatabase, name: str) -> None:
        self.db = db
        self.name = name

    async def insert_one(self, doc: dict[str, Any]) -> Any:
        oid = doc.get("_id") or ObjectId()
        doc["_id"] = oid
        self.db.reviews[str(oid)] = doc
        return type("InsertRes", (), {"inserted_id": oid})()

    async def find_one(self, query: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        if self.name in {"repositories", "repos"}:
            qid = str(query.get("_id", ""))
            return self.db.repos.get(qid)
        if self.name == "reviews":
            qid = str(query.get("_id", ""))
            return self.db.reviews.get(qid)
        return None

    def find(self, query: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        repo_id = str(query.get("repo_id", ""))
        items = [r for r in self.db.reviews.values() if str(r.get("repo_id")) == repo_id]

        class MockCursor:
            def __init__(self, data: list[dict[str, Any]]) -> None:
                self.data = data

            def sort(self, *args: Any, **kwargs: Any) -> MockCursor:
                return self

            def limit(self, *args: Any, **kwargs: Any) -> MockCursor:
                return self

            async def to_list(self, length: int) -> list[dict[str, Any]]:
                return self.data[:length]

        return MockCursor(items)

    async def update_one(
        self, query: dict[str, Any], update: dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        qid = str(query.get("_id", ""))
        target = self.db.reviews.get(qid)
        if target and "$set" in update:
            target.update(update["$set"])
        return type("UpdateRes", (), {"modified_count": 1 if target else 0})()


@pytest.mark.asyncio
async def test_reviews_api_end_to_end_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        DATA_DIR=".",
        LLM_PROVIDER="fake",
        LLM_MODEL="fake-model",
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)

    mock_db = MockReviewsDatabase()
    repo_id = "607f1f77bcf86cd799439011"
    user_id = "607f1f77bcf86cd799439021"

    # Pre-seed repository document
    mock_db.repos[repo_id] = {
        "_id": ObjectId(repo_id),
        "name": "my-task-app",
        "display_name": "Task App",
        "owner_id": user_id,
        "last_synced_commit": "abcdef123456",
    }

    # Inject mock mongo collections
    monkeypatch.setattr(mongo, "get_collection", mock_db.get_collection)
    monkeypatch.setattr(mongo, "get_database", lambda: mock_db)
    monkeypatch.setattr(mongo, "get_mongo_client", lambda: mock_db)
    monkeypatch.setattr("app.core.deps.get_database", lambda: mock_db)
    monkeypatch.setattr(mongo, "_mongo_client", mock_db)

    # Mock FileRepository to return sample base content
    async def mock_get_by_path(self: Any, r_id: str, path: str) -> dict[str, Any]:
        return {
            "path": path,
            "content": "import db\n\ndef list_user_tasks(user_id: int):\n    return db.query(user_id)\n",
        }

    monkeypatch.setattr(FileRepository, "get_by_path", mock_get_by_path)

    app = create_app()

    # Override authentication dependencies
    from app.db.mongo import get_database

    app.dependency_overrides[get_database] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: {
        "_id": ObjectId(user_id),
        "email": "reviewer@example.com",
        "role": "admin",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Review from Diff Upload (multipart/form-data)
        upload_resp = await client.post(
            f"/api/v1/repos/{repo_id}/reviews",
            files={"file": ("patch_01.diff", SAMPLE_DIFF.encode("utf-8"), "text/plain")},
        )
        assert upload_resp.status_code == 201, upload_resp.text
        review_data = upload_resp.json()
        review_id = review_data["id"]
        assert review_data["status"] == "completed"
        assert review_data["risk_level"] == "critical"
        assert review_data["stats"]["files_changed"] == 1
        assert len(review_data["findings"]) >= 1

        # Locate SQL injection finding
        sql_finding = next(
            (f for f in review_data["findings"] if "SQL Injection" in f["title"]),
            None,
        )
        assert sql_finding is not None
        assert sql_finding["severity"] == "critical"
        assert sql_finding["category"] == "security"
        finding_id = sql_finding["id"]

        # 2. List Reviews for Repository
        list_resp = await client.get(f"/api/v1/repos/{repo_id}/reviews")
        assert list_resp.status_code == 200
        reviews_list = list_resp.json()
        assert len(reviews_list) >= 1
        assert reviews_list[0]["id"] == review_id

        # 3. Get Review by ID
        get_resp = await client.get(f"/api/v1/reviews/{review_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == review_id

        # Anti-enumeration test for non-existent review
        missing_resp = await client.get("/api/v1/reviews/607f1f77bcf86cd799439999")
        assert missing_resp.status_code == 404

        # 4. Accept Finding
        patch_finding_resp = await client.patch(
            f"/api/v1/reviews/{review_id}/findings/{finding_id}",
            json={"status": "accepted", "user_note": "Approved by security lead."},
        )
        assert patch_finding_resp.status_code == 200
        updated_rev = patch_finding_resp.json()
        assert updated_rev["stats"]["accepted_count"] == 1
        updated_f = next(f for f in updated_rev["findings"] if f["id"] == finding_id)
        assert updated_f["status"] == "accepted"
        assert updated_f["user_note"] == "Approved by security lead."

        # 5. Export Review as Markdown
        export_md = await client.get(f"/api/v1/reviews/{review_id}/export?format=markdown")
        assert export_md.status_code == 200
        assert "text/markdown" in export_md.headers["content-type"]
        md_text = export_md.text
        assert "# Code Review Report" in md_text
        assert "SQL Injection" in md_text
        assert "CRITICAL" in md_text

        # 6. Export Review as JSON
        export_json = await client.get(f"/api/v1/reviews/{review_id}/export?format=json")
        assert export_json.status_code == 200
        assert "application/json" in export_json.headers["content-type"]

        # 7. Evaluate Suite against Seeded Patches (§10.6)
        eval_resp = await client.get("/api/v1/eval/reviews")
        assert eval_resp.status_code == 200
        eval_metrics = eval_resp.json()
        assert eval_metrics["patches_evaluated"] == 6
        assert eval_metrics["total_seeded"] == 6
        assert eval_metrics["matched_seeded"] == 6
        assert eval_metrics["detection_recall"] == 1.0
        assert eval_metrics["strict_recall"] >= 0.83


@pytest.mark.asyncio
@respx.mock
async def test_reviews_github_fetch_and_publish_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_db = MockReviewsDatabase()
    repo_id = "607f1f77bcf86cd799439011"
    user_id = "607f1f77bcf86cd799439022"

    mock_db.repos[repo_id] = {
        "_id": ObjectId(repo_id),
        "name": "Hello-World",
        "display_name": "Hello-World",
        "owner_id": user_id,
        "last_synced_commit": "old_base_commit_111",
    }

    monkeypatch.setattr(mongo, "get_collection", mock_db.get_collection)
    monkeypatch.setattr(mongo, "get_database", lambda: mock_db)
    monkeypatch.setattr(mongo, "get_mongo_client", lambda: mock_db)
    monkeypatch.setattr("app.core.deps.get_database", lambda: mock_db)
    monkeypatch.setattr(mongo, "_mongo_client", mock_db)

    async def mock_get_by_path(self: Any, r_id: str, path: str) -> dict[str, Any]:
        return {"path": path, "content": "def hello(): pass\n"}

    monkeypatch.setattr(FileRepository, "get_by_path", mock_get_by_path)

    # Mock GitHub REST API calls via respx
    def github_pr_router(request: httpx.Request) -> httpx.Response:
        if "vnd.github.v3.diff" in request.headers.get("accept", ""):
            return httpx.Response(200, text=SAMPLE_DIFF)
        return httpx.Response(
            200,
            json={
                "title": "Fix security vulnerability",
                "body": "PR description",
                "base": {"sha": "different_base_222"},
                "head": {"sha": "head_333"},
            },
        )

    respx.get("https://api.github.com/repos/octocat/Hello-World/pulls/42").mock(
        side_effect=github_pr_router
    )
    respx.post("https://api.github.com/repos/octocat/Hello-World/pulls/42/reviews").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 98765432,
                "html_url": "https://github.com/octocat/Hello-World/pull/42#pullrequestreview-98765432",
            },
        )
    )

    app = create_app()
    from app.db.mongo import get_database

    app.dependency_overrides[get_database] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: {
        "_id": ObjectId(user_id),
        "email": "octo@example.com",
        "role": "admin",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create review from GitHub PR URL
        pr_resp = await client.post(
            f"/api/v1/repos/{repo_id}/reviews",
            json={"pr_url": "https://github.com/octocat/Hello-World/pull/42"},
        )
        assert pr_resp.status_code == 201, pr_resp.text
        review_data = pr_resp.json()
        review_id = review_data["id"]
        assert review_data["source"]["type"] == "github"
        assert review_data["source"]["pr_number"] == 42
        assert (
            review_data["indexed_commit_mismatch"] is True
        )  # old_base_commit_111 != different_base_222

        # Finding should be present
        assert len(review_data["findings"]) >= 1
        finding_id = review_data["findings"][0]["id"]

        # Accept finding
        await client.patch(
            f"/api/v1/reviews/{review_id}/findings/{finding_id}",
            json={"status": "accepted"},
        )

        # 2. Publish accepted findings to GitHub (§10.5)
        publish_resp = await client.post(
            f"/api/v1/reviews/{review_id}/publish",
            json={"comments_only": True, "github_token": "gh_mock_pat_token_test"},
        )
        assert publish_resp.status_code == 200, publish_resp.text
        published_data = publish_resp.json()
        assert published_data["published_to_github"] is True
        assert published_data["github_review_id"] == "98765432"
        assert "98765432" in published_data["github_review_url"]
