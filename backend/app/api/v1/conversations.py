from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.messages import MessageRepository
from app.db.repositories.repos import RepositoryRepository
from app.schemas.chat import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    ExportResponse,
    MessageResponse,
    SendMessageRequest,
)
from app.services.chat.service import ChatService

router = APIRouter(tags=["chat"])


def get_conversation_repository() -> ConversationRepository:
    return ConversationRepository()


def get_message_repository() -> MessageRepository:
    return MessageRepository()


def get_repo_repository() -> RepositoryRepository:
    return RepositoryRepository()


def get_chat_service(
    settings: Settings = Depends(get_settings),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    msg_repo: MessageRepository = Depends(get_message_repository),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
) -> ChatService:
    return ChatService(
        settings=settings,
        conversation_repo=conv_repo,
        message_repo=msg_repo,
        repo_repo=repo_repo,
    )


def _format_conversation(doc: dict[str, Any]) -> ConversationResponse:
    return ConversationResponse(
        id=str(doc["_id"]),
        repo_id=str(doc["repo_id"]),
        user_id=str(doc["user_id"]),
        title=doc.get("title", "New Conversation"),
        message_count=doc.get("message_count", 0),
        created_at=doc["created_at"],
        updated_at=doc.get("updated_at", doc["created_at"]),
    )


def _format_message(doc: dict[str, Any]) -> MessageResponse:
    return MessageResponse(
        id=str(doc["_id"]),
        conversation_id=str(doc["conversation_id"]),
        user_id=str(doc["user_id"]),
        role=doc["role"],
        content=doc.get("content", ""),
        status=doc.get("status", "complete"),
        route=doc.get("route"),
        sources=doc.get("sources", []),
        citations=doc.get("citations", []),
        confidence=doc.get("confidence"),
        usage=doc.get("usage"),
        latency_ms=doc.get("latency_ms", {}),
        trace=doc.get("trace", {}),
        cached=doc.get("cached", False),
        feedback=doc.get("feedback"),
        created_at=doc["created_at"],
    )


# --- Repository Scoped Conversations ---


@router.get(
    "/repos/{repo_id}/conversations",
    response_model=ConversationListResponse,
    summary="List conversations for repository (§12)",
)
async def list_conversations(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
) -> ConversationListResponse:
    user_id = str(user["_id"])
    repo = await repo_repo.get_by_id(repo_id)
    if not repo:
        raise NotFoundError("Repository not found.")

    docs = await conv_repo.list_by_repo_user(repo_id, user_id)
    return ConversationListResponse(items=[_format_conversation(d) for d in docs])


@router.post(
    "/repos/{repo_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation (§12)",
)
async def create_conversation(
    repo_id: str,
    payload: ConversationCreate,
    user: dict[str, Any] = Depends(get_current_user),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
) -> ConversationResponse:
    user_id = str(user["_id"])
    repo = await repo_repo.get_by_id(repo_id)
    if not repo:
        raise NotFoundError("Repository not found.")

    title = payload.title or "New Conversation"
    doc = await conv_repo.create(repo_id=repo_id, user_id=user_id, title=title)
    return _format_conversation(doc)


# --- Conversation Scoped Operations ---


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation detail with message history (§12)",
)
async def get_conversation_detail(
    conversation_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    msg_repo: MessageRepository = Depends(get_message_repository),
) -> ConversationDetailResponse:
    user_id = str(user["_id"])
    conv = await conv_repo.get_by_id(conversation_id)
    if not conv or conv["user_id"] != user_id:
        raise NotFoundError("Conversation not found.")

    messages = await msg_repo.list_by_conversation(conversation_id)
    return ConversationDetailResponse(
        conversation=_format_conversation(conv),
        messages=[_format_message(m) for m in messages],
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Rename conversation (§12)",
)
async def rename_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user: dict[str, Any] = Depends(get_current_user),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationResponse:
    user_id = str(user["_id"])
    conv = await conv_repo.get_by_id(conversation_id)
    if not conv or conv["user_id"] != user_id:
        raise NotFoundError("Conversation not found.")

    await conv_repo.update_title(conversation_id, payload.title)
    updated = await conv_repo.get_by_id(conversation_id)
    if not updated:
        raise NotFoundError("Conversation not found.")
    return _format_conversation(updated)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation (§12)",
)
async def delete_conversation(
    conversation_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    msg_repo: MessageRepository = Depends(get_message_repository),
) -> Response:
    user_id = str(user["_id"])
    conv = await conv_repo.get_by_id(conversation_id)
    if not conv or conv["user_id"] != user_id:
        raise NotFoundError("Conversation not found.")

    await msg_repo.delete_by_conversation(conversation_id)
    await conv_repo.delete(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/conversations/{conversation_id}/export",
    response_model=ExportResponse,
    summary="Export conversation to Markdown (§9.9, §12)",
)
async def export_conversation(
    conversation_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ExportResponse:
    user_id = str(user["_id"])
    markdown, filename = await chat_service.export_markdown(conversation_id, user_id)
    return ExportResponse(markdown=markdown, filename=filename)


@router.post(
    "/conversations/{conversation_id}/messages",
    summary="Send message and stream response via SSE (§9.8, §12)",
)
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    user: dict[str, Any] = Depends(get_current_user),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Streams response tokens and events via text/event-stream (§9.8)."""
    user_id = str(user["_id"])
    conv = await conv_repo.get_by_id(conversation_id)
    if not conv or conv["user_id"] != user_id:
        raise NotFoundError("Conversation not found.")

    async def event_generator() -> AsyncIterator[str]:
        async for event in chat_service.stream_message(
            conversation_id=conversation_id,
            user_id=user_id,
            content=payload.content,
            strategy=payload.strategy,
            regenerate_of=payload.regenerate_of,
        ):
            event_name = event.get("event", "message")
            data_str = event.get("data", "")
            yield f"event: {event_name}\ndata: {data_str}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
