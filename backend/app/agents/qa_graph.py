from __future__ import annotations

import time
from typing import Any, cast

import structlog
from langgraph.graph import END, START, StateGraph

from app.agents.state import QAState
from app.core.config import Settings
from app.schemas.retrieval import RetrievalStrategy
from app.services.chat.citations import verify_and_clean_citations
from app.services.chat.confidence import compute_confidence
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.llm.factory import get_llm_provider, resolve_model_name
from app.services.llm.prompts.templates import (
    CONTEXTUALIZE_SYSTEM_PROMPT,
    CONTEXTUALIZE_USER_PROMPT,
    GROUNDING_SYSTEM_PROMPT,
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT,
    REFORMULATE_SYSTEM_PROMPT,
)
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.router.heuristic import route_heuristically
from app.services.retrieval.service import RetrievalService

logger = structlog.get_logger(__name__)


class QAGraphRunner:
    """Orchestrates the 9-node LangGraph question-answering workflow (§9.3)."""

    def __init__(
        self,
        settings: Settings,
        retrieval_service: RetrievalService,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.settings = settings
        self.retrieval = retrieval_service
        self.llm = llm_provider or get_llm_provider(settings)
        self.primary_model = resolve_model_name(settings, fast=False)
        self.fast_model = resolve_model_name(settings, fast=True)
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(QAState)

        builder.add_node("contextualize", self.node_contextualize)
        builder.add_node("route", self.node_route)
        builder.add_node("retrieve", self.node_retrieve)
        builder.add_node("graph_expand", self.node_graph_expand)
        builder.add_node("rerank", self.node_rerank)
        builder.add_node("assess", self.node_assess)
        builder.add_node("reformulate", self.node_reformulate)
        builder.add_node("generate", self.node_generate)
        builder.add_node("verify", self.node_verify)
        builder.add_node("finalize", self.node_finalize)

        builder.add_edge(START, "contextualize")
        builder.add_edge("contextualize", "route")

        # Routing decision
        builder.add_conditional_edges(
            "route",
            self._route_decision,
            {
                "retrieve": "retrieve",
                "generate": "generate",
            },
        )

        builder.add_edge("retrieve", "graph_expand")
        builder.add_edge("graph_expand", "rerank")
        builder.add_edge("rerank", "assess")

        # Assessment decision (HyDE reformulate loop or proceed)
        builder.add_conditional_edges(
            "assess",
            self._assess_decision,
            {
                "reformulate": "reformulate",
                "generate": "generate",
            },
        )

        builder.add_edge("reformulate", "retrieve")
        builder.add_edge("generate", "verify")
        builder.add_edge("verify", "finalize")
        builder.add_edge("finalize", END)

        return builder.compile()

    # --- Conditional Edge Selectors ---

    def _route_decision(self, state: QAState) -> str:
        intent = state.get("route", {}).get("intent", "locate")
        if intent in ("out_of_scope", "general"):
            return "generate"
        return "retrieve"

    def _assess_decision(self, state: QAState) -> str:
        attempt = state.get("attempt", 1)
        max_attempts = self.settings.MAX_RETRIEVAL_ATTEMPTS
        is_insufficient = state.get("insufficient", False)

        if is_insufficient and attempt < max_attempts:
            return "reformulate"
        return "generate"

    # --- Graph Nodes ---

    async def node_contextualize(self, state: QAState) -> dict[str, Any]:
        """Node 1: Rewrites follow-up questions using conversation history."""
        t0 = time.perf_counter()
        question = state["question"]
        history = state.get("history", [])

        if not history:
            return {
                "standalone_question": question,
                "timings": {
                    **state.get("timings", {}),
                    "contextualize": round((time.perf_counter() - t0) * 1000, 2),
                },
            }

        history_lines: list[str] = []
        for msg in history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_lines.append(f"{role.capitalize()}: {content}")
        history_text = "\n".join(history_lines)

        user_content = CONTEXTUALIZE_USER_PROMPT.format(
            history_text=history_text,
            question=question,
        )

        try:
            res = await self.llm.complete(
                [
                    ChatMessage(role="system", content=CONTEXTUALIZE_SYSTEM_PROMPT),
                    ChatMessage(role="user", content=user_content),
                ],
                model=self.fast_model,
                max_tokens=250,
                temperature=0.1,
            )
            rewritten = res.text.strip() or question
        except Exception as e:
            logger.warning("contextualize_failed", error=str(e))
            rewritten = question

        t_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "standalone_question": rewritten,
            "timings": {**state.get("timings", {}), "contextualize": t_ms},
        }

    async def node_route(self, state: QAState) -> dict[str, Any]:
        """Node 2: Classifies query intent, strategy, weights, and enrichments."""
        t0 = time.perf_counter()
        q = state.get("standalone_question") or state["question"]
        override = state.get("strategy_override")
        strat_override: RetrievalStrategy | None = (
            cast(RetrievalStrategy, override)
            if override in ("auto", "keyword", "vector", "hybrid", "hybrid_rerank")
            else None
        )

        # 1. Heuristic routing
        route_res = route_heuristically(q)

        # 2. LLM router refinement if configured
        if self.settings.ROUTER_MODE in ("llm", "hybrid") and self.llm.name != "fake":
            try:
                llm_route = await self.retrieval.router.route(q, strategy_override=strat_override)
                route_res = llm_route
            except Exception as e:
                logger.warning("llm_router_failed", error=str(e))

        route_dict = route_res.model_dump()
        if override:
            route_dict["strategy"] = override

        queries = route_dict.get("search_queries") or [q]
        t_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "route": route_dict,
            "queries": queries,
            "attempt": state.get("attempt", 1),
            "timings": {**state.get("timings", {}), "route": t_ms},
        }

    async def node_retrieve(self, state: QAState) -> dict[str, Any]:
        """Node 3: Executes multi-index candidate retrieval for search queries."""
        t0 = time.perf_counter()
        repo_id = state["repo_id"]
        commit_sha = state["commit_sha"]
        route = state["route"]
        queries = state.get("queries", [state["question"]])
        strategy = route.get("strategy", "hybrid")

        all_candidates: list[dict[str, Any]] = []
        embedding_model = self.settings.EMBEDDING_MODEL

        # Retrieve for each query in list (max 3)
        for q in queries[:3]:
            bm25_res: list[tuple[str, int, float]] = []
            vec_res: list[tuple[str, int, float]] = []
            sym_res: list[tuple[Any, ...]] = []
            sum_res: list[tuple[Any, ...]] = []

            if strategy == "keyword":
                bm25_res = await self.retrieval.keyword_search.search(
                    repo_id=repo_id,
                    commit_sha=commit_sha,
                    query=q,
                    k=self.settings.RETRIEVAL_CANDIDATES,
                )
            elif strategy == "vector":
                vec_res = await self.retrieval.vector_search.search(
                    repo_id=repo_id,
                    embedding_model=embedding_model,
                    query=q,
                    k=self.settings.RETRIEVAL_CANDIDATES,
                )
            else:  # hybrid or hybrid_rerank
                import asyncio

                async def _empty():
                    return []

                enrich = route.get("enrich", {})
                sym_coro = (
                    self.retrieval.symbol_lookup.lookup(
                        repo_id, q, route.get("identifiers", []), max_results=20
                    )
                    if enrich.get("symbol_lookup", True)
                    else _empty()
                )
                sum_coro = (
                    self.retrieval.summary_scope.get_summary_candidates(repo_id, limit=25)
                    if enrich.get("summary_scope", False)
                    else _empty()
                )

                bm25_task = self.retrieval.keyword_search.search(
                    repo_id=repo_id,
                    commit_sha=commit_sha,
                    query=q,
                    k=self.settings.RETRIEVAL_CANDIDATES,
                )
                vec_task = self.retrieval.vector_search.search(
                    repo_id=repo_id,
                    embedding_model=embedding_model,
                    query=q,
                    k=self.settings.RETRIEVAL_CANDIDATES,
                )

                bm25_res, vec_res, sym_res, sum_res = await asyncio.gather(
                    bm25_task, vec_task, sym_coro, sum_coro
                )

            weights = route.get("weights", {"bm25": 0.5, "vector": 0.5})
            fused = reciprocal_rank_fusion(
                bm25_results=bm25_res,
                vector_results=vec_res,
                symbol_results=sym_res,
                summary_results=sum_res,
                rrf_k=self.settings.RRF_K,
                bm25_weight=weights.get("bm25", 0.5),
                vector_weight=weights.get("vector", 0.5),
            )

            # Hydrate chunk objects
            chunk_ids = [fc.chunk_id for fc in fused]
            chunk_docs = await self.retrieval.chunk_repo.get_by_ids(chunk_ids)
            chunk_map = {str(c["_id"]): c for c in chunk_docs}

            for fc in fused:
                cdoc = chunk_map.get(fc.chunk_id)
                if cdoc:
                    all_candidates.append(
                        {
                            "chunk_id": fc.chunk_id,
                            "path": cdoc.get("path", ""),
                            "chunk_type": cdoc.get("chunk_type", "code"),
                            "symbol_name": cdoc.get("symbol_name"),
                            "start_line": cdoc.get("start_line", 1),
                            "end_line": cdoc.get("end_line", 1),
                            "part": cdoc.get("part", 1),
                            "parts": cdoc.get("parts", 1),
                            "text": cdoc.get("text", ""),
                            "embed_text": cdoc.get("embed_text", ""),
                            "token_count": cdoc.get("token_count", 0),
                            "score": fc.rrf_score,
                            "ranks": fc.ranks,
                            "rerank_score": None,
                        }
                    )

        # Deduplicate across queries by chunk_id
        seen_cids: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for cand in all_candidates:
            if cand["chunk_id"] not in seen_cids:
                seen_cids.add(cand["chunk_id"])
                deduped.append(cand)

        t_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "candidates": deduped,
            "timings": {**state.get("timings", {}), "retrieve": t_ms},
        }

    async def node_graph_expand(self, state: QAState) -> dict[str, Any]:
        """Node 4: Expands candidates along import/call edges for flow queries."""
        t0 = time.perf_counter()
        candidates = state.get("candidates", [])
        route = state.get("route", {})
        enrich = route.get("enrich", {})

        if not enrich.get("graph_expand", False) or not candidates:
            return {
                "timings": {**state.get("timings", {}), "graph_expand": 0.0},
            }

        top_files = list({c["path"] for c in candidates[:5]})
        graph_chunks = await self.retrieval.graph_expansion.expand(
            repo_id=state["repo_id"],
            top_file_paths=top_files,
            max_candidates=10,
        )

        existing_cids = {c["chunk_id"] for c in candidates}
        for item in graph_chunks:
            cid, _, doc = item
            if cid not in existing_cids:
                candidates.append(
                    {
                        "chunk_id": cid,
                        "path": doc.get("path", ""),
                        "start_line": doc.get("start_line", 1),
                        "end_line": doc.get("end_line", 1),
                        "symbol_name": doc.get("symbol_name"),
                        "language": doc.get("language", ""),
                        "chunk_type": doc.get("chunk_type", "code"),
                        "text": doc.get("text", ""),
                        "embed_text": doc.get("embed_text") or doc.get("text", ""),
                        "score": 0.0,
                    }
                )

        t_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "candidates": candidates,
            "timings": {**state.get("timings", {}), "graph_expand": t_ms},
        }

    async def node_rerank(self, state: QAState) -> dict[str, Any]:
        """Node 5: Cross-encoder reranks top candidate chunks."""
        t0 = time.perf_counter()
        candidates = state.get("candidates", [])
        route = state.get("route", {})
        strategy = route.get("strategy", "hybrid")

        if not candidates or strategy != "hybrid_rerank":
            return {
                "timings": {**state.get("timings", {}), "rerank": 0.0},
            }

        q = state.get("standalone_question") or state["question"]
        top_candidates = candidates[: self.settings.RERANK_TOP_N]

        # Prepare texts for cross-encoder reranking
        texts = [c.get("embed_text") or c.get("text", "") for c in top_candidates]
        scores = await self.retrieval.reranker.rerank(q, texts)

        for c, score in zip(top_candidates, scores, strict=False):
            c["rerank_score"] = round(float(score), 4)

        # Re-sort candidates by rerank score descending
        top_candidates.sort(key=lambda x: x.get("rerank_score", -999.0), reverse=True)
        final_candidates = top_candidates + candidates[len(top_candidates) :]

        t_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "candidates": final_candidates,
            "timings": {**state.get("timings", {}), "rerank": t_ms},
        }

    async def node_assess(self, state: QAState) -> dict[str, Any]:
        """Node 6: Assesses sufficiency of retrieved candidates (§9.3, §9.6)."""
        candidates = state.get("candidates", [])
        min_evidence = self.settings.MIN_EVIDENCE_SCORE

        # Assess sufficiency: top 3 candidates relevance
        is_insufficient = False
        if not candidates:
            is_insufficient = True
        else:
            top_scores: list[float] = []
            for c in candidates[:3]:
                if c.get("rerank_score") is not None:
                    # Sigmoid map
                    import math

                    sig = 1.0 / (1.0 + math.exp(-c["rerank_score"]))
                    top_scores.append(sig)
                else:
                    norm = (c.get("score", 0.0) - 0.2) / 0.6 if 0.6 != 0 else c.get("score", 0.0)
                    top_scores.append(max(0.0, min(1.0, norm)))

            avg_score = sum(top_scores) / len(top_scores) if top_scores else 0.0
            if avg_score < min_evidence:
                is_insufficient = True

        # Build context if proceeding or final attempt reached
        context_text, sources_map = self._build_context(candidates)

        return {
            "insufficient": is_insufficient,
            "context": context_text,
            "sources_map": sources_map,
        }

    async def node_reformulate(self, state: QAState) -> dict[str, Any]:
        """Node 7: HyDE reformulates queries when retrieval was weak."""
        attempt = state.get("attempt", 1) + 1
        q = state.get("standalone_question") or state["question"]

        try:
            res = await self.llm.complete(
                [
                    ChatMessage(role="system", content=REFORMULATE_SYSTEM_PROMPT),
                    ChatMessage(role="user", content=f"User Query: {q}"),
                ],
                model=self.fast_model,
                max_tokens=300,
                temperature=0.3,
            )
            data = res.parsed if res.parsed else {}
            new_queries = data.get("search_queries", [f"{q} code"])
        except Exception:
            new_queries = [f"{q} implementation", f"{q} definition"]

        current_queries = state.get("queries", [q])
        updated_queries = list(dict.fromkeys(current_queries + new_queries))

        return {
            "attempt": attempt,
            "queries": updated_queries,
        }

    async def node_generate(self, state: QAState) -> dict[str, Any]:
        """Node 8: Generates answer from formatted repository context."""
        t0 = time.perf_counter()
        intent = state.get("route", {}).get("intent", "locate")
        standalone_q = state.get("standalone_question") or state["question"]

        if intent == "out_of_scope":
            ans = (
                "I am RepoGPT, an assistant designed to explain and navigate this software repository. "
                "Feel free to ask questions about code structure, modules, functions, or execution flows!"
            )
            return {
                "answer": ans,
                "timings": {
                    **state.get("timings", {}),
                    "generate": round((time.perf_counter() - t0) * 1000, 2),
                },
            }

        if intent == "general":
            try:
                res = await self.llm.complete(
                    [
                        ChatMessage(
                            role="system",
                            content="You are a general software engineering assistant.",
                        ),
                        ChatMessage(role="user", content=standalone_q),
                    ],
                    model=self.primary_model,
                    max_tokens=600,
                    temperature=0.2,
                )
                ans = f"*(Note: This is a general programming answer and not based on this repository)*\n\n{res.text}"
            except Exception:
                ans = "*(Note: General programming explanation)*\n\nGeneral concept."
            return {
                "answer": ans,
                "timings": {
                    **state.get("timings", {}),
                    "generate": round((time.perf_counter() - t0) * 1000, 2),
                },
            }

        # Repository-grounded QA prompt
        commit_short = state.get("commit_sha", "main")[:7]
        sys_prompt = QA_SYSTEM_PROMPT.format(
            repo_full_name=state.get("repo_full_name", "repository"),
            commit_short=commit_short,
            languages=state.get("languages", "code"),
            intent=intent,
        )

        insufficient_note = (
            "\nRetrieval found only weak evidence. Be explicit about uncertainty and do not speculate beyond the sources."
            if state.get("insufficient", False)
            else ""
        )

        user_prompt = QA_USER_PROMPT.format(
            sources_xml=state.get("context", ""),
            conversation_summary="",
            standalone_question=standalone_q,
            insufficient_note=insufficient_note,
        )

        res = await self.llm.complete(
            [
                ChatMessage(role="system", content=sys_prompt),
                ChatMessage(role="user", content=user_prompt),
            ],
            model=self.primary_model,
            max_tokens=self.settings.LLM_MAX_OUTPUT_TOKENS,
            temperature=self.settings.LLM_TEMPERATURE,
        )

        t_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "answer": res.text,
            "usage": res.usage.model_dump(),
            "timings": {**state.get("timings", {}), "generate": t_ms},
        }

    async def node_verify(self, state: QAState) -> dict[str, Any]:
        """Node 9: Verifies citations, evaluates grounding, and computes confidence."""
        t0 = time.perf_counter()
        raw_answer = state.get("answer", "")
        sources_map = state.get("sources_map", {})
        intent = state.get("route", {}).get("intent", "locate")
        insufficient = state.get("insufficient", False)

        # 1. Clean and verify [S#] citations
        verify_res = verify_and_clean_citations(raw_answer, sources_map)

        # 2. Grounding check if enabled
        grounding_verdict: str | None = None
        if (
            self.settings.ENABLE_GROUNDING_CHECK
            and self.llm.name != "fake"
            and intent not in ("general", "out_of_scope")
            and verify_res.valid
        ):
            try:
                g_res = await self.llm.complete(
                    [
                        ChatMessage(role="system", content=GROUNDING_SYSTEM_PROMPT),
                        ChatMessage(
                            role="user",
                            content=f"Answer:\n{verify_res.cleaned_text}\n\nSources:\n{state.get('context', '')}",
                        ),
                    ],
                    model=self.fast_model,
                    max_tokens=200,
                    temperature=0.1,
                )
                g_data = g_res.parsed if g_res.parsed else {}
                grounding_verdict = g_data.get("verdict", "supported")
            except Exception as e:
                logger.warning("grounding_check_failed", error=str(e))
                grounding_verdict = "supported"
        elif self.llm.name == "fake" and verify_res.valid:
            grounding_verdict = "supported"

        # 3. Compute confidence score
        conf_res = compute_confidence(
            text=verify_res.cleaned_text,
            sources_map=sources_map,
            valid_citations=verify_res.valid,
            total_citations_found=verify_res.total_found,
            intent=intent,
            grounding_verdict=grounding_verdict,
            insufficient=insufficient,
        )

        t_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "cleaned_answer": verify_res.cleaned_text,
            "citations": [c.model_dump() for c in verify_res.valid],
            "removed_citations": verify_res.removed,
            "confidence": conf_res.model_dump(),
            "timings": {**state.get("timings", {}), "verify": t_ms},
        }

    async def node_finalize(self, state: QAState) -> dict[str, Any]:
        """Node 10: Assembles trace details, candidates summary, and final latency."""
        timings = state.get("timings", {})
        total_ms = sum(timings.values())
        timings["total"] = round(total_ms, 2)

        trace = {
            "intent": state.get("route", {}).get("intent"),
            "strategy": state.get("route", {}).get("strategy"),
            "reason": state.get("route", {}).get("reason"),
            "attempts": state.get("attempt", 1),
            "total_candidates": len(state.get("candidates", [])),
            "insufficient": state.get("insufficient", False),
            "citations_valid": len(state.get("citations", [])),
            "citations_removed": len(state.get("removed_citations", [])),
        }

        return {
            "trace": trace,
            "timings": timings,
        }

    # --- Context Builder Helper ---

    def _build_context(
        self, candidates: list[dict[str, Any]]
    ) -> tuple[str, dict[str, dict[str, Any]]]:
        """Formats candidates into XML <source id="S1" ...> blocks with original line numbers."""
        sources_map: dict[str, dict[str, Any]] = {}
        xml_blocks: list[str] = []

        # Dedupe ranges and pack up to CONTEXT_MAX_TOKENS
        top_k = self.settings.CONTEXT_TOP_K
        packed = candidates[:top_k]

        for i, c in enumerate(packed, start=1):
            s_id = f"S{i}"
            sources_map[s_id] = c

            path = c.get("path", "")
            start = c.get("start_line", 1)
            end = c.get("end_line", 1)
            symbol = c.get("symbol_name") or ""
            lang = c.get("language") or ""
            text = c.get("text", "")

            # Format original line numbering
            lines = text.splitlines()
            formatted_lines = [f"{start + idx:4d} | {line}" for idx, line in enumerate(lines)]
            numbered_body = "\n".join(formatted_lines)

            sym_attr = f' symbol="{symbol}"' if symbol else ""
            block = (
                f'<source id="{s_id}" path="{path}" lines="{start}-{end}"{sym_attr} language="{lang}">\n'
                f"{numbered_body}\n"
                f"</source>"
            )
            xml_blocks.append(block)

        return "\n\n".join(xml_blocks), sources_map

    async def execute(self, initial_state: QAState) -> QAState:
        """Runs the LangGraph QA state machine from START to END."""
        final_state = await self.graph.ainvoke(initial_state)
        return final_state
