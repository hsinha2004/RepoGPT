from __future__ import annotations

import fnmatch
import time
from typing import Any

import structlog

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository
from app.db.repositories.graph import GraphRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.symbols import SymbolRepository
from app.schemas.retrieval import (
    RetrievedChunk,
    RouteResult,
    SearchRequest,
    SearchResponse,
)
from app.services.retrieval.context_builder import ContextBuilder
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.graph_expansion import GraphExpansionService
from app.services.retrieval.keyword_search import KeywordSearchService
from app.services.retrieval.reranker import get_reranker_provider
from app.services.retrieval.router.router import QueryRouter
from app.services.retrieval.summary_scope import SummaryScopeService
from app.services.retrieval.symbol_lookup import SymbolLookupService
from app.services.retrieval.vector_search import VectorSearchService

logger = structlog.get_logger(__name__)


class RetrievalService:
    def __init__(
        self,
        settings: Settings,
        repo_repository: RepositoryRepository | None = None,
        chunk_repository: ChunkRepository | None = None,
        file_repository: FileRepository | None = None,
        symbol_repository: SymbolRepository | None = None,
        graph_repository: GraphRepository | None = None,
    ) -> None:
        self.settings = settings
        self.repo_repo = repo_repository or RepositoryRepository()
        self.chunk_repo = chunk_repository or ChunkRepository()
        self.file_repo = file_repository or FileRepository()
        self.symbol_repo = symbol_repository or SymbolRepository()
        self.graph_repo = graph_repository or GraphRepository()

        self.router = QueryRouter(settings)
        self.keyword_search = KeywordSearchService(settings)
        self.vector_search = VectorSearchService(settings)
        self.symbol_lookup = SymbolLookupService(self.symbol_repo, self.chunk_repo)
        self.graph_expansion = GraphExpansionService(self.graph_repo, self.chunk_repo)
        self.summary_scope = SummaryScopeService(self.chunk_repo, self.file_repo)
        self.reranker = get_reranker_provider(settings)
        self.context_builder = ContextBuilder(
            max_tokens=settings.CONTEXT_MAX_TOKENS,
            max_chunks=settings.CONTEXT_TOP_K,
        )

    async def search(
        self,
        repo_id: str,
        request: SearchRequest,
    ) -> SearchResponse:
        """Executes multi-index retrieval pipeline according to routed strategy."""
        t_total_start = time.perf_counter()
        latencies: dict[str, float] = {}

        # 1. Fetch repo and verify indexed commit
        repo = await self.repo_repo.get_by_id(repo_id)
        if not repo:
            raise NotFoundError("Repository not found")

        commit_sha = repo.get("commit_sha") or "HEAD"
        embedding_info = repo.get("embedding", {})
        embedding_model = embedding_info.get("model") or self.settings.EMBEDDING_MODEL

        # 2. Query routing
        t0 = time.perf_counter()
        route: RouteResult = await self.router.route(
            query=request.query,
            strategy_override=request.strategy,
        )
        latencies["route"] = round((time.perf_counter() - t0) * 1000, 2)

        # 3. Retrieve candidates
        t1 = time.perf_counter()
        bm25_res: list[tuple[str, int, float]] = []
        vec_res: list[tuple[str, int, float]] = []
        sym_res: list[tuple[Any, ...]] = []
        sum_res: list[tuple[Any, ...]] = []

        active_strategy = route.strategy
        k_candidates = self.settings.RETRIEVAL_CANDIDATES

        if active_strategy == "keyword":
            bm25_res = await self.keyword_search.search(
                repo_id=repo_id,
                commit_sha=commit_sha,
                query=request.query,
                k=k_candidates,
            )
        elif active_strategy == "vector":
            vec_res = await self.vector_search.search(
                repo_id=repo_id,
                embedding_model=embedding_model,
                query=request.query,
                k=k_candidates,
            )
        else:  # hybrid or hybrid_rerank
            import asyncio

            async def _empty_results() -> list[Any]:
                return []

            sym_coro = (
                self.symbol_lookup.lookup(
                    repo_id=repo_id,
                    query=request.query,
                    identifiers=route.identifiers,
                    max_results=20,
                )
                if route.enrich.symbol_lookup
                else _empty_results()
            )

            sum_coro = (
                self.summary_scope.get_summary_candidates(
                    repo_id=repo_id,
                    limit=25,
                )
                if route.enrich.summary_scope
                else _empty_results()
            )

            bm25_task = self.keyword_search.search(
                repo_id=repo_id,
                commit_sha=commit_sha,
                query=request.query,
                k=k_candidates,
            )
            vec_task = self.vector_search.search(
                repo_id=repo_id,
                embedding_model=embedding_model,
                query=request.query,
                k=k_candidates,
            )

            r_bm25, r_vec, r_sym, r_sum = await asyncio.gather(
                bm25_task, vec_task, sym_coro, sum_coro, return_exceptions=True
            )

            bm25_res = r_bm25 if isinstance(r_bm25, list) else []
            vec_res = r_vec if isinstance(r_vec, list) else []
            sym_res = r_sym if isinstance(r_sym, list) else []
            sum_res = r_sum if isinstance(r_sum, list) else []

        # Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion(
            bm25_results=bm25_res,
            vector_results=vec_res,
            symbol_results=sym_res,
            summary_results=sum_res,
            rrf_k=self.settings.RRF_K,
            bm25_weight=route.weights.bm25,
            vector_weight=route.weights.vector,
            symbol_weight=1.0,
            summary_weight=0.7,
        )
        latencies["retrieve"] = round((time.perf_counter() - t1) * 1000, 2)

        # 4. Graph expansion if requested (for flow/dependency queries)
        if route.enrich.graph_expand and fused:
            t2 = time.perf_counter()
            # Find top files from current top candidates
            temp_cids = [c.chunk_id for c in fused[:10]]
            top_temp_chunks = await self.chunk_repo.get_by_ids(temp_cids)
            top_paths = [str(c["path"]) for c in top_temp_chunks if c.get("path")]
            top_paths = list(dict.fromkeys(top_paths))

            graph_res = await self.graph_expansion.expand(
                repo_id=repo_id,
                top_file_paths=top_paths,
                max_candidates=10,
            )
            if graph_res:
                fused = reciprocal_rank_fusion(
                    bm25_results=bm25_res,
                    vector_results=vec_res,
                    symbol_results=sym_res,
                    graph_results=graph_res,
                    summary_results=sum_res,
                    rrf_k=self.settings.RRF_K,
                    bm25_weight=route.weights.bm25,
                    vector_weight=route.weights.vector,
                    symbol_weight=1.0,
                    graph_weight=0.8,
                )
            latencies["graph_expand"] = round((time.perf_counter() - t2) * 1000, 2)

        if not fused:
            latencies["total"] = round((time.perf_counter() - t_total_start) * 1000, 2)
            return SearchResponse(
                query=request.query,
                route=route,
                results=[],
                context="<sources>\n</sources>",
                total_candidates=0,
                latency_ms=latencies,
            )

        # 5. Hydrate candidate documents from MongoDB
        top_cids = [c.chunk_id for c in fused[: self.settings.RERANK_TOP_N]]
        docs = await self.chunk_repo.get_by_ids(top_cids)
        doc_map = {str(d.get("_id") or d.get("chunk_id")): d for d in docs}

        candidates: list[RetrievedChunk] = []
        for fc in fused[: self.settings.RERANK_TOP_N]:
            doc = doc_map.get(fc.chunk_id) or fc.raw_doc
            if not doc:
                continue

            chunk_id = str(doc.get("_id") or doc.get("chunk_id") or fc.chunk_id)
            path = doc.get("path", "")
            language = doc.get("language", "")

            # Apply filters if requested
            if request.file_pattern and not fnmatch.fnmatch(path, request.file_pattern):
                continue
            if request.language and language.lower() != request.language.lower():
                continue

            chunk = RetrievedChunk(
                chunk_id=chunk_id,
                repo_id=repo_id,
                commit_sha=commit_sha,
                path=path,
                language=language,
                chunk_type=doc.get("chunk_type", "code"),
                symbol_name=doc.get("symbol_name"),
                symbol_kind=doc.get("symbol_kind"),
                parent_symbol=doc.get("parent_symbol"),
                start_line=doc.get("start_line", 1),
                end_line=doc.get("end_line", 1),
                part=doc.get("part", 1),
                parts=doc.get("parts", 1),
                text=doc.get("text", ""),
                embed_text=doc.get("embed_text", doc.get("text", "")),
                token_count=doc.get("token_count", 0),
                score=round(fc.rrf_score, 5),
                ranks=fc.ranks,
            )
            candidates.append(chunk)

        # 6. Reranking if strategy is hybrid_rerank (or auto chose hybrid_rerank)
        if active_strategy == "hybrid_rerank" and candidates:
            t3 = time.perf_counter()
            texts_to_rerank = [c.embed_text for c in candidates]
            rerank_scores = await self.reranker.rerank(
                query=request.query,
                texts=texts_to_rerank,
            )
            for c, r_score in zip(candidates, rerank_scores, strict=False):
                c.rerank_score = r_score
                # Update chunk score to rerank score
                c.score = r_score

            # Sort descending by rerank score
            candidates.sort(key=lambda x: x.rerank_score or 0.0, reverse=True)
            latencies["rerank"] = round((time.perf_counter() - t3) * 1000, 2)

        # 7. Context building
        t4 = time.perf_counter()
        context_xml, selected_chunks = self.context_builder.build_context(candidates)
        latencies["context"] = round((time.perf_counter() - t4) * 1000, 2)

        latencies["total"] = round((time.perf_counter() - t_total_start) * 1000, 2)

        # Top-k results
        k_results = selected_chunks[: request.top_k]

        return SearchResponse(
            query=request.query,
            route=route,
            results=k_results,
            context=context_xml,
            total_candidates=len(candidates),
            latency_ms=latencies,
        )
