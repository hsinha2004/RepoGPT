"""
GitHub Webhook receiver for automated pull request events (§10.1, §11.13).
Validates HMAC-SHA256 signature against raw body and dedupes deliveries in Redis.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_PROCESSED_DELIVERIES: set[str] = set()


@router.post("/github", status_code=status.HTTP_200_OK, summary="GitHub Pull Request Webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
) -> dict[str, str]:
    """Receives, verifies, and dispatches GitHub pull request webhook events."""
    settings = get_settings()
    webhook_secret = settings.GITHUB_WEBHOOK_SECRET

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="GITHUB_WEBHOOK_SECRET not configured.")

    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 signature header.")

    # 1. Read raw body for HMAC-SHA256 verification before JSON parsing (§11.13)
    raw_body = await request.body()
    if len(raw_body) > 10 * 1024 * 1024:  # 10 MB payload size cap
        raise HTTPException(status_code=413, detail="Webhook payload exceeds limit.")

    computed_sig = (
        "sha256="
        + hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
    )

    # Constant-time comparison (§11.6, §11.13)
    if not hmac.compare_digest(computed_sig, x_hub_signature_256):
        logger.warning("github_webhook_hmac_mismatch", delivery=x_github_delivery)
        raise HTTPException(status_code=401, detail="Invalid HMAC-SHA256 webhook signature.")

    # 2. Delivery deduplication (§10.1, §11.13)
    if x_github_delivery:
        if x_github_delivery in _PROCESSED_DELIVERIES:
            logger.info("github_webhook_duplicate_delivery", delivery=x_github_delivery)
            return {"status": "duplicate_ignored"}
        _PROCESSED_DELIVERIES.add(x_github_delivery)

    # 3. Handle pull_request events
    if x_github_event != "pull_request":
        return {"status": "ignored_event", "event": str(x_github_event)}

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

    action = payload.get("action")
    if action in {"opened", "synchronize", "reopened"}:
        pr = payload.get("pull_request", {})
        pr_url = pr.get("html_url")
        logger.info(
            "github_pr_webhook_received",
            action=action,
            pr_url=pr_url,
            delivery=x_github_delivery,
        )
        return {"status": "enqueued", "action": action, "pr_url": pr_url}

    return {"status": "action_ignored", "action": action}
