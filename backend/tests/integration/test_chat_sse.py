import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.conversations import (
    get_chat_service,
    get_conversation_repository,
    get_message_repository,
    get_repo_repository,
)
from app.api.v1.messages import get_message_repository as get_msg_repo_feedback
from app.core.deps import get_current_user
from app.main import create_app


class MockConversationRepo:
    def __init__(self):
        self.convs = {}
        self._seq = 1

    async def create(self, repo_id: str, user_id: str, title: str):
        cid = f"conv_{self._seq}"
        self._seq += 1
        doc = {
            "_id": cid,
            "repo_id": repo_id,
            "user_id": user_id,
            "title": title,
            "message_count": 0,
            "created_at": "2026-10-12T00:00:00Z",
            "updated_at": "2026-10-12T00:00:00Z",
        }
        self.convs[cid] = doc
        return doc

    async def get_by_id(self, conversation_id: str):
        return self.convs.get(conversation_id)

    async def list_by_repo_user(self, repo_id: str, user_id: str, limit: int = 50):
        res = [
            c for c in self.convs.values() if c["repo_id"] == repo_id and c["user_id"] == user_id
        ]
        return res[:limit]

    async def update_title(self, conversation_id: str, title: str):
        if conversation_id in self.convs:
            self.convs[conversation_id]["title"] = title
            return True
        return False

    async def increment_message_count(self, conversation_id: str, delta: int = 1):
        if conversation_id in self.convs:
            self.convs[conversation_id]["message_count"] = (
                self.convs[conversation_id].get("message_count", 0) + delta
            )

    async def delete(self, conversation_id: str):
        if conversation_id in self.convs:
            del self.convs[conversation_id]
            return True
        return False


class MockMessageRepo:
    def __init__(self):
        self.msgs = {}
        self._seq = 1

    async def create(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        status: str = "complete",
        **kwargs,
    ):
        mid = f"msg_{self._seq}"
        self._seq += 1
        doc = {
            "_id": mid,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "status": status,
            "citations": [],
            "created_at": "2026-10-12T00:00:00Z",
            "feedback": None,
            **kwargs,
        }
        self.msgs[mid] = doc
        return doc

    async def get_by_id(self, message_id: str):
        return self.msgs.get(message_id)

    async def list_by_conversation(self, conversation_id: str, limit: int = 100):
        res = [m for m in self.msgs.values() if m["conversation_id"] == conversation_id]
        return res[:limit]

    async def update_feedback(self, message_id: str, rating: str, comment: str | None = None):
        if message_id in self.msgs:
            self.msgs[message_id]["feedback"] = {
                "rating": rating,
                "comment": comment,
                "at": "2026-10-12T00:00:00Z",
            }
            return True
        return False

    async def update_status(self, message_id: str, status: str, content: str | None = None):
        if message_id in self.msgs:
            self.msgs[message_id]["status"] = status
            if content is not None:
                self.msgs[message_id]["content"] = content
            return True
        return False

    async def delete_by_conversation(self, conversation_id: str):
        keys = [k for k, v in self.msgs.items() if v["conversation_id"] == conversation_id]
        for k in keys:
            del self.msgs[k]
        return len(keys)


class MockRepoRepo:
    def __init__(self):
        self.repos = {}

    async def get_by_id(self, repo_id: str):
        return self.repos.get(repo_id)


@pytest.fixture
def chat_app():
    app = create_app()
    conv_repo = MockConversationRepo()
    msg_repo = MockMessageRepo()
    repo_repo = MockRepoRepo()

    user_id = "user_test_chat"
    repo_id = "repo_test_123"

    repo_repo.repos[repo_id] = {
        "_id": repo_id,
        "display_name": "TaskFlow",
        "owner_id": user_id,
        "commit_sha": "abc1234",
        "stats": {"languages": {"Python": 1200, "TypeScript": 800}},
    }

    mock_chat_service = MagicMock()

    async def mock_stream(
        conversation_id, user_id, content, strategy="auto", regenerate_of=None
    ):
        _ = (user_id, content, strategy, regenerate_of)
        yield {
            "event": "meta",
            "data": json.dumps(
                {
                    "message_id": "msg_2",
                    "conversation_id": conversation_id,
                    "user_message_id": "msg_1",
                }
            ),
        }
        yield {
            "event": "status",
            "data": json.dumps({"stage": "routing", "detail": "Classifying query intent"}),
        }
        yield {
            "event": "route",
            "data": json.dumps(
                {
                    "intent": "locate",
                    "strategy": "hybrid_rerank",
                    "weights": {"bm25": 0.5, "vector": 0.5},
                    "enrich": {
                        "symbol_lookup": True,
                        "graph_expand": False,
                        "summary_scope": False,
                    },
                    "identifiers": ["create_access_token"],
                    "search_queries": ["create_access_token"],
                    "reason": "Locates JWT token creation function",
                }
            ),
        }
        yield {
            "event": "status",
            "data": json.dumps({"stage": "retrieving", "detail": "Retrieving candidates"}),
        }
        yield {
            "event": "sources",
            "data": json.dumps(
                [
                    {
                        "id": "S1",
                        "path": "backend/app/auth/security.py",
                        "start_line": 25,
                        "end_line": 40,
                        "symbol": "create_access_token",
                        "language": "python",
                        "chunk_type": "code",
                        "snippet": "def create_access_token():\n    return 'jwt'",
                        "scores": {"rrf": 0.85, "rerank": 2.4},
                    }
                ]
            ),
        }
        yield {
            "event": "status",
            "data": json.dumps({"stage": "generating", "detail": "Synthesizing answer"}),
        }
        yield {"event": "token", "data": json.dumps({"text": "The JWT token is created "})}
        yield {"event": "token", "data": json.dumps({"text": "in `security.py` [S1]. "})}
        yield {
            "event": "citations",
            "data": json.dumps(
                {
                    "valid": [
                        {
                            "source_id": "S1",
                            "path": "backend/app/auth/security.py",
                            "start_line": 25,
                            "end_line": 40,
                            "symbol": "create_access_token",
                        }
                    ],
                    "removed": [],
                }
            ),
        }
        yield {
            "event": "confidence",
            "data": json.dumps(
                {
                    "score": 0.92,
                    "label": "High",
                    "factors": {"r": 0.95, "c": 1.0, "k": 1.0, "g": 1.0},
                    "insufficient": False,
                }
            ),
        }
        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "usage": {
                        "prompt_tokens": 120,
                        "completion_tokens": 25,
                        "total_tokens": 145,
                        "cost_usd": 0.0,
                    },
                    "latency_ms": {"total": 45.2},
                    "cached": False,
                }
            ),
        }

    mock_chat_service.stream_message = mock_stream
    mock_chat_service.export_markdown = AsyncMock(
        return_value=("# Chat Export\n\n- [S1] `backend/app/auth/security.py:25-40`", "chat.md")
    )

    app.dependency_overrides[get_current_user] = lambda: {
        "_id": user_id,
        "email": "tester@repogpt.local",
        "role": "user",
    }
    app.dependency_overrides[get_conversation_repository] = lambda: conv_repo
    app.dependency_overrides[get_message_repository] = lambda: msg_repo
    app.dependency_overrides[get_msg_repo_feedback] = lambda: msg_repo
    app.dependency_overrides[get_repo_repository] = lambda: repo_repo
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

    return app, conv_repo, msg_repo, repo_id, user_id


@pytest.mark.asyncio
async def test_chat_lifecycle_and_sse_streaming(chat_app) -> None:
    app, conv_repo, msg_repo, repo_id, user_id = chat_app
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a conversation
        create_res = await client.post(
            f"/api/v1/repos/{repo_id}/conversations",
            json={"title": "TaskFlow QA"},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert create_res.status_code == 201
        conv_data = create_res.json()
        conv_id = conv_data["id"]
        assert conv_data["title"] == "TaskFlow QA"

        # 2. List conversations
        list_res = await client.get(
            f"/api/v1/repos/{repo_id}/conversations",
            headers={"Authorization": "Bearer fake_token"},
        )
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == conv_id

        # 3. Rename conversation
        patch_res = await client.patch(
            f"/api/v1/conversations/{conv_id}",
            json={"title": "Updated Title"},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "Updated Title"

        # 4. Stream message via SSE
        stream_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Where is create_access_token?", "strategy": "auto"},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers["content-type"]

        # Parse SSE events from response text
        body_text = stream_res.text
        lines = body_text.splitlines()
        events: list[tuple[str, str]] = []
        current_event = "message"

        for line in lines:
            if line.startswith("event: "):
                current_event = line.replace("event: ", "").strip()
            elif line.startswith("data: "):
                data_val = line.replace("data: ", "").strip()
                events.append((current_event, data_val))

        event_names = [e[0] for e in events]
        assert "meta" in event_names
        assert "route" in event_names
        assert "sources" in event_names
        assert "token" in event_names
        assert "citations" in event_names
        assert "confidence" in event_names
        assert "done" in event_names

        # 5. Export conversation
        export_res = await client.get(
            f"/api/v1/conversations/{conv_id}/export",
            headers={"Authorization": "Bearer fake_token"},
        )
        assert export_res.status_code == 200
        export_data = export_res.json()
        assert "markdown" in export_data
        assert "filename" in export_data

        # 6. Delete conversation
        del_res = await client.delete(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": "Bearer fake_token"},
        )
        assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_message_feedback(chat_app) -> None:
    app, conv_repo, msg_repo, repo_id, user_id = chat_app

    # Seed an assistant message
    msg_doc = await msg_repo.create(
        conversation_id="conv_1",
        user_id=user_id,
        role="assistant",
        content="Answer text",
    )
    msg_id = str(msg_doc["_id"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/messages/{msg_id}/feedback",
            json={"rating": "up", "comment": "Accurate citations"},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert res.status_code == 200
        fb_data = res.json()
        assert fb_data["rating"] == "up"
        assert fb_data["comment"] == "Accurate citations"
