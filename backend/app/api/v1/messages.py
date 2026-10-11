from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.repositories.messages import MessageRepository
from app.schemas.chat import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/messages", tags=["chat"])


def get_message_repository() -> MessageRepository:
    return MessageRepository()


@router.post(
    "/{message_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit user feedback on assistant message (§9.9, §12)",
)
async def submit_message_feedback(
    message_id: str,
    payload: FeedbackRequest,
    user: dict[str, Any] = Depends(get_current_user),
    msg_repo: MessageRepository = Depends(get_message_repository),
) -> FeedbackResponse:
    user_id = str(user["_id"])
    msg = await msg_repo.get_by_id(message_id)
    if not msg or msg["user_id"] != user_id:
        raise NotFoundError("Message not found.")

    await msg_repo.update_feedback(
        message_id=message_id,
        rating=payload.rating,
        comment=payload.comment,
    )

    updated = await msg_repo.get_by_id(message_id)
    if not updated or not updated.get("feedback"):
        raise NotFoundError("Message not found.")

    fb = updated["feedback"]
    return FeedbackResponse(
        rating=fb["rating"],
        comment=fb.get("comment"),
        at=fb["at"],
    )
