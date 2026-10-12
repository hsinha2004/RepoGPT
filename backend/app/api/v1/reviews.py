"""
FastAPI endpoints for Phase 2: Pull Request Code Review (§10, §12.6).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response, status
from starlette.datastructures import UploadFile

from app.core.deps import get_current_user, require_repo_access
from app.core.errors import BadRequestError, NotFoundError
from app.db.repositories.files import FileRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.reviews import ReviewRepository
from app.db.repositories.symbols import SymbolRepository
from app.schemas.review import (
    PublishReviewRequest,
    ReviewFindingUpdate,
    ReviewResponse,
)
from app.services.review.service import ReviewService

router = APIRouter(tags=["reviews"])


def get_review_repository() -> ReviewRepository:
    return ReviewRepository()


def get_review_service(
    review_repo: ReviewRepository = Depends(get_review_repository),
) -> ReviewService:
    return ReviewService(
        review_repo=review_repo,
        repo_repo=RepositoryRepository(),
        file_repo=FileRepository(),
        symbol_repo=SymbolRepository(),
    )


def _format_review_response(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "repo_id": str(doc["repo_id"]),
        "user_id": str(doc["user_id"]),
        "source": doc.get("source", {}),
        "status": doc.get("status", "pending"),
        "risk_level": doc.get("risk_level", "low"),
        "stats": doc.get("stats", {}),
        "summary": doc.get("summary", ""),
        "file_walkthrough": doc.get("file_walkthrough", []),
        "findings": doc.get("findings", []),
        "general_comments": doc.get("general_comments", []),
        "published_to_github": doc.get("published_to_github", False),
        "github_review_id": doc.get("github_review_id"),
        "github_review_url": doc.get("github_review_url"),
        "error": doc.get("error"),
        "indexed_commit_mismatch": doc.get("indexed_commit_mismatch", False),
        "created_at": doc.get("created_at", "").isoformat()
        if hasattr(doc.get("created_at"), "isoformat")
        else str(doc.get("created_at", "")),
        "updated_at": doc.get("updated_at", "").isoformat()
        if hasattr(doc.get("updated_at"), "isoformat")
        else str(doc.get("updated_at", "")),
    }


@router.post(
    "/repos/{repo_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger code review from PR URL or diff upload",
)
async def create_review(
    repo_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    _repo_access: dict[str, Any] = Depends(require_repo_access("editor")),
    review_service: ReviewService = Depends(get_review_service),
) -> dict[str, Any]:
    """Triggers automated code review via PR URL or uploaded .diff/.patch file."""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise BadRequestError("Patch file required for multipart diff review.")
        diff_bytes = await file.read()
        diff_text = diff_bytes.decode("utf-8", errors="replace")
        filename = file.filename or "uploaded.patch"

        review_doc = await review_service.create_review_from_diff(
            repo_id=repo_id,
            user_id=str(current_user["_id"]),
            diff_text=diff_text,
            patch_filename=filename,
        )
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        pr_url = body.get("pr_url")
        if not pr_url:
            raise BadRequestError("pr_url string or multipart .diff file required.")

        review_doc = await review_service.create_review_from_pr(
            repo_id=repo_id,
            user_id=str(current_user["_id"]),
            pr_url=pr_url,
        )

    return _format_review_response(review_doc)


@router.get(
    "/repos/{repo_id}/reviews",
    response_model=list[ReviewResponse],
    summary="List reviews for repository",
)
async def list_reviews(
    repo_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] = Depends(get_current_user),
    _repo_access: dict[str, Any] = Depends(require_repo_access("viewer")),
    review_repo: ReviewRepository = Depends(get_review_repository),
) -> list[dict[str, Any]]:
    """Lists past code reviews for the repository."""
    docs = await review_repo.list_for_repo(repo_id, limit=limit)
    return [_format_review_response(d) for d in docs]


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Get code review details and findings",
)
async def get_review(
    review_id: str,
    _current_user: dict[str, Any] = Depends(get_current_user),
    review_repo: ReviewRepository = Depends(get_review_repository),
) -> dict[str, Any]:
    """Retrieves review walkthrough, findings, and risk scoring."""
    doc = await review_repo.get_by_id(review_id)
    if not doc:
        # Anti-Enumeration §7.5, §11.7
        raise NotFoundError("Review not found", code="REVIEW_NOT_FOUND")

    return _format_review_response(doc)


@router.patch(
    "/reviews/{review_id}/findings/{finding_id}",
    response_model=ReviewResponse,
    summary="Accept, reject, or edit review finding",
)
async def update_finding(
    review_id: str,
    finding_id: str,
    payload: ReviewFindingUpdate,
    _current_user: dict[str, Any] = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
) -> dict[str, Any]:
    """Updates finding acceptance status or modifies title, severity, or notes."""
    doc = await review_service.review_repo.get_by_id(review_id)
    if not doc:
        raise NotFoundError("Review not found", code="REVIEW_NOT_FOUND")

    updated = await review_service.review_repo.update_finding(
        review_id=review_id,
        finding_id=finding_id,
        updates=payload.model_dump(exclude_unset=True),
    )
    if not updated:
        raise NotFoundError("Finding not found in review", code="FINDING_NOT_FOUND")

    return _format_review_response(updated)


@router.post(
    "/reviews/{review_id}/publish",
    response_model=ReviewResponse,
    summary="Publish accepted review comments to GitHub",
)
async def publish_review(
    review_id: str,
    payload: PublishReviewRequest = PublishReviewRequest(),
    current_user: dict[str, Any] = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
) -> dict[str, Any]:
    """Publishes accepted review findings to GitHub as a COMMENT review (§10.5)."""
    doc = await review_service.review_repo.get_by_id(review_id)
    if not doc:
        raise NotFoundError("Review not found", code="REVIEW_NOT_FOUND")

    user_id = str(current_user["_id"])
    token = payload.github_token or current_user.get("github_token") or getattr(review_service.settings, "GITHUB_TOKEN", None)
    published = await review_service.publish_to_github(
        review_id=review_id,
        user_id=user_id,
        custom_token=token,
    )
    return _format_review_response(published)


@router.get(
    "/reviews/{review_id}/export",
    summary="Export review report as Markdown",
)
async def export_review(
    review_id: str,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
    _current_user: dict[str, Any] = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
) -> Response:
    """Exports review report as downloadable Markdown or JSON."""
    doc = await review_service.review_repo.get_by_id(review_id)
    if not doc:
        raise NotFoundError("Review not found", code="REVIEW_NOT_FOUND")

    if format == "json":
        return Response(
            content=str(_format_review_response(doc)),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="review_{review_id}.json"'},
        )

    md_content = review_service.export_markdown(doc)
    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="review_{review_id}.md"'},
    )
