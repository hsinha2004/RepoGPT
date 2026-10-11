from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

import structlog

from app.agents.qa_graph import QAGraphRunner
from app.agents.state import QAState
from app.core.config import Settings
from app.core.errors import NotFoundError
from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.messages import MessageRepository
from app.db.repositories.repos import RepositoryRepository
from app.services.chat.cache import AnswerCache, build_answer_cache_key
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.llm.prompts.templates import PROMPT_VERSION
from app.services.retrieval.service import RetrievalService

logger = structlog.get_logger(__name__)


class ChatService:
    """Manages conversations, message history, answer caching, and SSE streaming (§9.8, §9.9)."""

    def __init__(
        self,
        settings: Settings,
        conversation_repo: ConversationRepository | None = None,
        message_repo: MessageRepository | None = None,
        repo_repo: RepositoryRepository | None = None,
        retrieval_service: RetrievalService | None = None,
        llm_provider: LLMProvider | None = None,
        answer_cache: AnswerCache | None = None,
    ) -> None:
        self.settings = settings
        self.conv_repo = conversation_repo or ConversationRepository()
        self.msg_repo = message_repo or MessageRepository()
        self.repo_repo = repo_repo or RepositoryRepository()
        self.retrieval = retrieval_service or RetrievalService(
            settings, repo_repository=self.repo_repo
        )
        self.llm = llm_provider or get_llm_provider(settings)
        self.cache = answer_cache or AnswerCache(
            None, ttl_seconds=settings.ANSWER_CACHE_TTL_SECONDS
        )
        self.qa_runner = QAGraphRunner(settings, self.retrieval, self.llm)

    async def stream_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        strategy: str = "auto",
        regenerate_of: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Executes QA agentic workflow and yields SSE events according to the protocol (§9.8)."""
        conv = await self.conv_repo.get_by_id(conversation_id)
        if not conv or conv["user_id"] != user_id:
            yield {
                "event": "error",
                "data": json.dumps({"code": "NOT_FOUND", "message": "Conversation not found."}),
            }
            return

        repo_id = conv["repo_id"]
        repo = await self.repo_repo.get_by_id(repo_id)
        if not repo:
            yield {
                "event": "error",
                "data": json.dumps({"code": "NOT_FOUND", "message": "Repository not found."}),
            }
            return

        commit_sha = repo.get("commit_sha", "main")
        repo_full_name = (
            repo.get("display_name") or repo.get("source", {}).get("name") or "repository"
        )
        languages_dict = repo.get("stats", {}).get("languages", {})
        languages_str = ", ".join(languages_dict.keys()) if languages_dict else "code"

        # 1. Persist user message
        user_msg = await self.msg_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=content,
        )
        await self.conv_repo.increment_message_count(conversation_id, 1)

        # Auto-update conversation title on first message
        if conv.get("message_count", 0) == 0 and (
            not conv.get("title") or conv["title"] == "New Conversation"
        ):
            first_title = content.strip().replace("\n", " ")[:60]
            await self.conv_repo.update_title(conversation_id, first_title)

        # 2. Emit meta event
        # Pre-create assistant placeholder doc to obtain message_id
        asst_msg = await self.msg_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content="",
            status="complete",
        )
        asst_msg_id = str(asst_msg["_id"])

        yield {
            "event": "meta",
            "data": json.dumps(
                {
                    "message_id": asst_msg_id,
                    "conversation_id": conversation_id,
                    "user_message_id": str(user_msg["_id"]),
                }
            ),
        }

        # 3. Check answer cache if first turn and not regenerate
        is_first_turn = conv.get("message_count", 0) <= 1 and not regenerate_of
        cache_key = build_answer_cache_key(
            repo_id=repo_id,
            commit_sha=commit_sha,
            embedding_model=self.settings.EMBEDDING_MODEL,
            strategy=strategy,
            prompt_version=PROMPT_VERSION,
            question=content,
        )

        if is_first_turn:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                # Replay cached answer sequence
                yield {
                    "event": "status",
                    "data": json.dumps({"stage": "routing", "detail": "Cached answer found"}),
                }
                yield {"event": "route", "data": json.dumps(cached_data.get("route", {}))}
                yield {"event": "sources", "data": json.dumps(cached_data.get("sources", []))}
                # Stream cached answer in chunks
                cached_text = cached_data.get("text", "")
                words = cached_text.split(" ")
                for i, w in enumerate(words):
                    token_text = w if i == len(words) - 1 else w + " "
                    yield {"event": "token", "data": json.dumps({"text": token_text})}
                    await asyncio.sleep(0.005)

                yield {"event": "citations", "data": json.dumps(cached_data.get("citations", {}))}
                yield {"event": "confidence", "data": json.dumps(cached_data.get("confidence", {}))}
                yield {
                    "event": "done",
                    "data": json.dumps(
                        {
                            "usage": cached_data.get("usage", {}),
                            "latency_ms": cached_data.get("latency_ms", {"total": 5.0}),
                            "cached": True,
                        }
                    ),
                }

                # Update assistant message
                await self.msg_repo.update_status(asst_msg_id, "complete", cached_text)
                await self.conv_repo.increment_message_count(conversation_id, 1)
                return

        # 4. Fetch recent conversation history
        past_msgs = await self.msg_repo.list_by_conversation(conversation_id, limit=8)
        history: list[dict[str, str]] = []
        for pm in past_msgs:
            if str(pm["_id"]) not in (str(user_msg["_id"]), asst_msg_id) and pm.get("content"):
                history.append({"role": pm["role"], "content": pm["content"]})

        # 5. Execute QA Graph
        t_start = time.perf_counter()
        yield {
            "event": "status",
            "data": json.dumps({"stage": "routing", "detail": "Classifying query intent"}),
        }

        initial_state: QAState = {
            "repo_id": repo_id,
            "commit_sha": commit_sha,
            "user_id": user_id,
            "repo_full_name": repo_full_name,
            "languages": languages_str,
            "question": content,
            "history": history,
            "strategy_override": strategy if strategy != "auto" else None,
            "attempt": 1,
            "timings": {},
        }

        try:
            # We run the nodes through the runner
            final_state = await self.qa_runner.execute(initial_state)

            # Route event
            route_dict = final_state.get("route", {})
            yield {"event": "route", "data": json.dumps(route_dict)}

            # Sources event
            sources_list: list[dict[str, Any]] = []
            for s_id, s_data in final_state.get("sources_map", {}).items():
                sources_list.append(
                    {
                        "id": s_id,
                        "path": s_data.get("path", ""),
                        "start_line": s_data.get("start_line", 1),
                        "end_line": s_data.get("end_line", 1),
                        "symbol": s_data.get("symbol_name"),
                        "language": s_data.get("language", ""),
                        "chunk_type": s_data.get("chunk_type", "code"),
                        "snippet": s_data.get("text", "")[:200],
                        "scores": {
                            "rrf": s_data.get("score", 0.0),
                            "rerank": s_data.get("rerank_score"),
                        },
                    }
                )
            yield {"event": "sources", "data": json.dumps(sources_list)}

            # Token streaming
            yield {
                "event": "status",
                "data": json.dumps({"stage": "generating", "detail": "Synthesizing answer"}),
            }
            full_text = final_state.get("cleaned_answer") or final_state.get("answer", "")
            words = full_text.split(" ")
            for i, w in enumerate(words):
                t_token = w if i == len(words) - 1 else w + " "
                yield {"event": "token", "data": json.dumps({"text": t_token})}
                await asyncio.sleep(0.005)

            # Citations event
            citations_data = {
                "valid": final_state.get("citations", []),
                "removed": final_state.get("removed_citations", []),
            }
            yield {"event": "citations", "data": json.dumps(citations_data)}

            # Confidence event
            conf_data = final_state.get("confidence", {})
            yield {"event": "confidence", "data": json.dumps(conf_data)}

            # Done event
            latency_ms = final_state.get("timings", {})
            latency_ms["total"] = round((time.perf_counter() - t_start) * 1000, 2)
            usage_data = final_state.get("usage", {})
            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "usage": usage_data,
                        "latency_ms": latency_ms,
                        "cached": False,
                    }
                ),
            }

            # Update assistant message in DB
            await self.msg_repo.update_status(asst_msg_id, "complete", full_text)
            await self.conv_repo.increment_message_count(conversation_id, 1)

            # Populate answer cache for first-turn questions
            if is_first_turn:
                to_cache = {
                    "text": full_text,
                    "route": route_dict,
                    "sources": sources_list,
                    "citations": citations_data,
                    "confidence": conf_data,
                    "usage": usage_data,
                    "latency_ms": latency_ms,
                }
                await self.cache.set(cache_key, to_cache)

        except asyncio.CancelledError:
            logger.info("sse_client_disconnected", conversation_id=conversation_id)
            await self.msg_repo.update_status(asst_msg_id, "stopped")
            raise
        except Exception as e:
            logger.exception("qa_workflow_failed", error=str(e))
            yield {
                "event": "error",
                "data": json.dumps(
                    {"code": "INTERNAL_ERROR", "message": f"Answer generation failed: {str(e)}"}
                ),
            }
            await self.msg_repo.update_status(asst_msg_id, "error")

    async def export_markdown(self, conversation_id: str, user_id: str) -> tuple[str, str]:
        """Exports full conversation as clean Markdown format with citations (§9.9)."""
        conv = await self.conv_repo.get_by_id(conversation_id)
        if not conv or conv["user_id"] != user_id:
            raise NotFoundError("Conversation not found.")

        repo = await self.repo_repo.get_by_id(conv["repo_id"])
        repo_name = repo.get("display_name") if repo else "Repository"

        messages = await self.msg_repo.list_by_conversation(conversation_id)

        lines: list[str] = [
            f"# Conversation: {conv.get('title', 'RepoGPT Chat')}",
            f"**Repository:** {repo_name}  ",
            f"**Exported:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  \n",
            "---",
        ]

        for m in messages:
            role_header = "### 👤 User" if m["role"] == "user" else "### 🤖 RepoGPT"
            lines.append(f"\n{role_header}\n")
            lines.append(m.get("content", ""))

            # If assistant with citations, append citation references
            citations = m.get("citations", [])
            if citations:
                lines.append("\n**Sources Cited:**")
                for c in citations:
                    s_id = c.get("source_id", "S#")
                    path = c.get("path", "")
                    start = c.get("start_line", 1)
                    end = c.get("end_line", 1)
                    lines.append(f"- `[{s_id}]` `{path}:{start}-{end}`")

            lines.append("\n---")

        md_content = "\n".join(lines)
        clean_title = (
            "".join(c for c in conv.get("title", "chat") if c.isalnum() or c in "-_ ")
            .strip()
            .replace(" ", "_")
        )
        filename = f"{clean_title or 'repogpt_chat'}.md"
        return md_content, filename
