"""
Integration tests for GitHub webhook receiver (§10.1, §11.13).
Validates HMAC-SHA256 signature calculation, constant-time comparison,
delivery deduplication, and pull request event handling.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

WEBHOOK_SECRET = "test-webhook-secret-key-12345"


def _calc_signature(secret: str, body: bytes) -> str:
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


@pytest.mark.asyncio
async def test_github_webhook_hmac_and_deduplication(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        DATA_DIR=".",
        GITHUB_WEBHOOK_SECRET=WEBHOOK_SECRET,
    )
    monkeypatch.setattr("app.api.v1.webhooks.get_settings", lambda: settings)

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "html_url": "https://github.com/octocat/Hello-World/pull/42",
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        valid_sig = _calc_signature(WEBHOOK_SECRET, body_bytes)

        # 1. Missing signature header -> 401
        res = await client.post(
            "/api/v1/webhooks/github",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-001",
            },
        )
        assert res.status_code == 401
        assert "Missing" in res.json()["detail"]

        # 2. Invalid signature header -> 401
        res = await client.post(
            "/api/v1/webhooks/github",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invaliddeadbeef",
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-001",
            },
        )
        assert res.status_code == 401
        assert "Invalid" in res.json()["detail"]

        # 3. Valid signature -> 200 enqueued
        res = await client.post(
            "/api/v1/webhooks/github",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": valid_sig,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-001",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "enqueued"
        assert data["action"] == "opened"
        assert data["pr_url"] == "https://github.com/octocat/Hello-World/pull/42"

        # 4. Duplicate delivery ID -> ignored / duplicate_ignored
        res_dup = await client.post(
            "/api/v1/webhooks/github",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": valid_sig,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-001",
            },
        )
        assert res_dup.status_code == 200
        assert res_dup.json()["status"] == "duplicate_ignored"

        # 5. Non-PR event -> ignored_event
        ping_payload = {"zen": "Keep it logically awesome."}
        ping_bytes = json.dumps(ping_payload).encode("utf-8")
        ping_sig = _calc_signature(WEBHOOK_SECRET, ping_bytes)

        res_ping = await client.post(
            "/api/v1/webhooks/github",
            content=ping_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": ping_sig,
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "delivery-002",
            },
        )
        assert res_ping.status_code == 200
        assert res_ping.json()["status"] == "ignored_event"
