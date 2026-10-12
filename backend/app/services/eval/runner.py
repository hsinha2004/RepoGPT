from __future__ import annotations

import time
from typing import Any, cast

import structlog

from app.core.config import Settings, get_settings
from app.db.repositories.benchmarks import BenchmarkRepository
from app.db.repositories.eval_runs import EvalRunRepository
from app.db.repositories.repos import RepositoryRepository
from app.schemas.eval import (
    CalibrationBin,
    EvalEstimateResponse,
    StrategyMetrics,
)
from app.schemas.retrieval import RetrievalStrategy, SearchRequest
from app.services.chat.citations import verify_and_clean_citations
from app.services.eval.metrics import (
    compute_brier_score,
    compute_citation_metrics,
    compute_ece_and_bins,
    compute_hit_at_k,
    compute_mrr,
    compute_must_mention_coverage,
    compute_ndcg_at_k,
    compute_percentiles,
    compute_precision_at_k,
    compute_recall_at_k,
    compute_symbol_recall_at_k,
)
from app.services.llm.base import ChatMessage, LLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.retrieval.service import RetrievalService

logger = structlog.get_logger(__name__)


class EvaluationRunner:
    """Orchestrates comprehensive multi-strategy benchmark evaluation (§14.2, §14.3)."""

    def __init__(
        self,
        settings: Settings | None = None,
        eval_repo: EvalRunRepository | None = None,
        benchmark_repo: BenchmarkRepository | None = None,
        repo_repo: RepositoryRepository | None = None,
        retrieval_service: RetrievalService | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.eval_repo = eval_repo or EvalRunRepository()
        self.benchmark_repo = benchmark_repo or BenchmarkRepository()
        self.repo_repo = repo_repo or RepositoryRepository()
        self.retrieval_service = retrieval_service or RetrievalService(self.settings)
        self.llm = llm or get_llm_provider(self.settings)

    def estimate_run(
        self,
        benchmark: dict[str, Any],
        strategies: list[str],
        generate_answers: bool = True,
        llm_judge: bool = False,
    ) -> EvalEstimateResponse:
        """Calculates pre-flight resource estimates for an evaluation run (§14.3)."""
        questions = benchmark.get("questions", [])
        q_count = len(questions)
        s_count = len(strategies)

        # Base retrieval calls: 0 LLM calls if purely keyword/vector, 1 route call if auto/hybrid
        llm_calls_per_q = 0
        if generate_answers:
            llm_calls_per_q += 1  # Generation call
            if llm_judge:
                llm_calls_per_q += 1

        total_llm_calls = q_count * s_count * max(llm_calls_per_q, 1) if generate_answers else 0
        avg_tokens_per_call = 1200
        total_tokens = total_llm_calls * avg_tokens_per_call

        # Cost estimation: approx $0.001 per 1k tokens
        cost_per_token = 0.000001
        estimated_cost_usd = round(total_tokens * cost_per_token, 4)

        # Duration estimation based on 60 RPM (1 call / sec) + search latency (~200ms)
        rpm = getattr(self.settings, "LLM_MAX_RPM", 60) or 60
        sec_per_call = 60.0 / rpm
        search_time_per_q = 0.25 * s_count
        total_duration = (total_llm_calls * sec_per_call) + (q_count * search_time_per_q)

        return EvalEstimateResponse(
            estimated_llm_calls=total_llm_calls,
            estimated_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            estimated_duration_seconds=round(max(total_duration, 5.0), 1),
            question_count=q_count,
            strategies_count=s_count,
        )

    async def run_evaluation(
        self,
        run_id: str,
        repo_id: str,
        benchmark_id: str,
        strategies: list[str],
        router_mode: str = "hybrid",
        k_values: list[int] | None = None,
        generate_answers: bool = True,
        llm_judge: bool = False,
        vector_store: str = "chroma",
        embedding_model: str | None = None,
    ) -> dict[str, Any]:
        """Executes full evaluation across questions and strategies, saving results."""
        _ = (router_mode, llm_judge, vector_store, embedding_model)
        ks = k_values or [1, 3, 5, 10]
        max_k = max(ks)

        benchmark = await self.benchmark_repo.get_benchmark(benchmark_id)
        if not benchmark:
            err = f"Benchmark {benchmark_id} not found."
            await self.eval_repo.fail_run(run_id, err)
            raise ValueError(err)

        questions = benchmark.get("questions", [])
        if not questions:
            err = f"Benchmark {benchmark_id} contains no questions."
            await self.eval_repo.fail_run(run_id, err)
            raise ValueError(err)

        await self.eval_repo.update_progress(run_id, progress=5, stage="Initializing evaluation...")

        all_question_results: list[dict[str, Any]] = []
        strategy_metrics_map: dict[str, StrategyMetrics] = {}
        latency_breakdown_map: dict[str, dict[str, float]] = {}
        category_breakdown_map: dict[str, dict[str, Any]] = {}

        total_steps = len(strategies) * len(questions)
        current_step = 0

        for strat in strategies:
            strat_results: list[dict[str, Any]] = []
            strat_latencies_total: list[float] = []
            strat_confidences: list[float] = []
            strat_correctness: list[float] = []

            hits_1, hits_3, hits_5, hits_10 = [], [], [], []
            prec_1, prec_3, prec_5, prec_10 = [], [], [], []
            rec_1, rec_3, rec_5, rec_10 = [], [], [], []
            mrrs, ndcgs_5, ndcgs_10 = [], [], []
            symbol_recalls = []
            intent_accuracies = []
            cit_validities, cit_precisions, cit_recalls = [], [], []
            must_mentions, answer_corrects = [], []
            tokens_list, costs_list = [], []

            route_times, retrieve_times, rerank_times, gen_times = [], [], [], []

            for q_idx, q_item in enumerate(questions):
                current_step += 1
                progress_pct = int(5 + (90 * (current_step / total_steps)))
                await self.eval_repo.update_progress(
                    run_id,
                    progress=progress_pct,
                    stage=f"Evaluating {strat} ({q_idx + 1}/{len(questions)})...",
                )

                q_text = q_item.get("question", "")
                q_id = q_item.get("id", f"q{q_idx + 1}")
                category = q_item.get("category", "locate")
                expected_intent = q_item.get("expected_intent", "locate")
                expected_files = q_item.get("expected_files", [])
                expected_symbols = q_item.get("expected_symbols", [])
                must_mention = q_item.get("must_mention", [])

                t0 = time.perf_counter()

                # 1. Search Request
                search_strat = cast(
                    RetrievalStrategy,
                    strat if strat != "auto" else "hybrid_rerank",
                )
                req = SearchRequest(
                    query=q_text,
                    strategy=search_strat,
                    top_k=max_k,
                )

                try:
                    search_res = await self.retrieval_service.search(repo_id, req)
                    retrieved_chunks = [c.model_dump() for c in search_res.results]
                    retrieved_files = [c["path"] for c in retrieved_chunks]
                    predicted_intent: str = search_res.route.intent
                    route_time = search_res.latency_ms.get("route", 0.0)
                    retrieve_time = search_res.latency_ms.get("retrieve", 0.0)
                    rerank_time = search_res.latency_ms.get("rerank", 0.0)
                except Exception as e:
                    logger.warning(
                        "eval_search_failed", question=q_id, strategy=strat, error=str(e)
                    )
                    retrieved_chunks = []
                    retrieved_files = []
                    predicted_intent = "unknown"
                    route_time = retrieve_time = rerank_time = 0.0

                route_times.append(route_time)
                retrieve_times.append(retrieve_time)
                rerank_times.append(rerank_time)

                # 2. Compute Retrieval Metrics
                h1 = compute_hit_at_k(retrieved_files, expected_files, 1)
                h3 = compute_hit_at_k(retrieved_files, expected_files, 3)
                h5 = compute_hit_at_k(retrieved_files, expected_files, 5)
                h10 = compute_hit_at_k(retrieved_files, expected_files, 10)
                hits_1.append(h1)
                hits_3.append(h3)
                hits_5.append(h5)
                hits_10.append(h10)

                p1 = compute_precision_at_k(retrieved_files, expected_files, 1)
                p3 = compute_precision_at_k(retrieved_files, expected_files, 3)
                p5 = compute_precision_at_k(retrieved_files, expected_files, 5)
                p10 = compute_precision_at_k(retrieved_files, expected_files, 10)
                prec_1.append(p1)
                prec_3.append(p3)
                prec_5.append(p5)
                prec_10.append(p10)

                r1 = compute_recall_at_k(retrieved_files, expected_files, 1)
                r3 = compute_recall_at_k(retrieved_files, expected_files, 3)
                r5 = compute_recall_at_k(retrieved_files, expected_files, 5)
                r10 = compute_recall_at_k(retrieved_files, expected_files, 10)
                rec_1.append(r1)
                rec_3.append(r3)
                rec_5.append(r5)
                rec_10.append(r10)

                mrr = compute_mrr(retrieved_files, expected_files)
                mrrs.append(mrr)

                ndcg5 = compute_ndcg_at_k(retrieved_chunks, expected_files, expected_symbols, 5)
                ndcg10 = compute_ndcg_at_k(retrieved_chunks, expected_files, expected_symbols, 10)
                ndcgs_5.append(ndcg5)
                ndcgs_10.append(ndcg10)

                sym_rec = compute_symbol_recall_at_k(retrieved_chunks, expected_symbols, 5)
                symbol_recalls.append(sym_rec)

                intent_acc = 1.0 if predicted_intent == expected_intent else 0.0
                intent_accuracies.append(intent_acc)

                # 3. Generation (if requested)
                answer_text: str | None = None
                citations: list[str] = []
                conf_score = 0.5
                cit_val = 0.0
                cit_prec = 0.0
                cit_rec = 0.0
                must_cov = 0.0
                ans_corr = False
                gen_time = 0.0
                tokens_used = 0
                cost_usd = 0.0

                if generate_answers and retrieved_chunks:
                    t_gen_0 = time.perf_counter()
                    # Build source list
                    sources_map = {
                        f"S{idx + 1}": {
                            "path": c["path"],
                            "start_line": c.get("start_line", 1),
                            "end_line": c.get("end_line", 1),
                            "symbol": c.get("symbol_name") or c.get("symbol"),
                        }
                        for idx, c in enumerate(retrieved_chunks[:5])
                    }
                    sources_str = "\n".join(
                        f'<source id="S{idx + 1}" path="{c["path"]}">\n{c.get("text", "")[:300]}\n</source>'
                        for idx, c in enumerate(retrieved_chunks[:5])
                    )
                    valid_sids = set(sources_map.keys())

                    sys_prompt = (
                        "You are RepoGPT answering questions about a codebase.\n"
                        "Rules:\n"
                        "1. Support every factual claim with inline [S#] citations.\n"
                        "2. Answer strictly based on <sources>."
                    )
                    user_prompt = (
                        f"<sources>\n{sources_str}\n</sources>\n\nQuestion: {q_text}\nAnswer:"
                    )

                    try:
                        llm_res = await self.llm.complete(
                            [
                                ChatMessage(role="system", content=sys_prompt),
                                ChatMessage(role="user", content=user_prompt),
                            ],
                            model=getattr(self.settings, "LLM_MODEL", "default") or "default",
                            max_tokens=600,
                            temperature=0.1,
                        )
                        answer_text = llm_res.text
                        gen_time = (time.perf_counter() - t_gen_0) * 1000.0

                        # Citations & Confidence
                        cit_res = verify_and_clean_citations(answer_text, sources_map)
                        answer_text = cit_res.cleaned_text
                        citations = [v.source_id for v in cit_res.valid]
                        cited_files = [v.path for v in cit_res.valid]

                        cit_metrics = compute_citation_metrics(
                            citations, cited_files, expected_files, valid_sids
                        )
                        cit_val = cit_metrics["validity"]
                        cit_prec = cit_metrics["precision"]
                        cit_rec = cit_metrics["recall"]

                        must_cov = compute_must_mention_coverage(answer_text, must_mention)
                        ans_corr = (must_cov >= 0.6 and cit_prec > 0.0) or (must_cov >= 0.8)

                        # Calibrated confidence formula: 0.35R + 0.20C + 0.15K + 0.30G
                        r_comp = min(h5, 1.0)
                        c_comp = cit_prec
                        k_comp = must_cov
                        g_comp = cit_val
                        conf_score = round(
                            0.35 * r_comp + 0.20 * c_comp + 0.15 * k_comp + 0.30 * g_comp, 4
                        )

                        tokens_used = llm_res.usage.total_tokens if llm_res.usage else 800
                        cost_usd = round(tokens_used * 0.000001, 5)

                    except Exception as e:
                        logger.warning("eval_generation_failed", error=str(e))
                        answer_text = "Generation unavailable."
                elif not generate_answers:
                    # Deterministic correctness proxy from retrieval
                    ans_corr = bool(h5 >= 1.0)
                    conf_score = 0.85 if ans_corr else 0.15

                gen_times.append(gen_time)
                cit_validities.append(cit_val)
                cit_precisions.append(cit_prec)
                cit_recalls.append(cit_rec)
                must_mentions.append(must_cov)
                answer_corrects.append(1.0 if ans_corr else 0.0)
                strat_confidences.append(conf_score)
                strat_correctness.append(1.0 if ans_corr else 0.0)
                tokens_list.append(tokens_used)
                costs_list.append(cost_usd)

                t_total = (time.perf_counter() - t0) * 1000.0
                strat_latencies_total.append(t_total)

                q_res = {
                    "run_id": run_id,
                    "question_id": q_id,
                    "question": q_text,
                    "category": category,
                    "expected_intent": expected_intent,
                    "expected_files": expected_files,
                    "expected_symbols": expected_symbols,
                    "strategy": strat,
                    "predicted_intent": predicted_intent,
                    "retrieved_files": retrieved_files[:5],
                    "hit_at_5": bool(h5 >= 1.0),
                    "reciprocal_rank": round(mrr, 4),
                    "generated_answer": answer_text,
                    "citations": citations,
                    "confidence": conf_score,
                    "citation_valid": bool(cit_val >= 0.99),
                    "citation_precision": round(cit_prec, 4),
                    "citation_recall": round(cit_rec, 4),
                    "must_mention_coverage": round(must_cov, 4),
                    "answer_correct": ans_corr,
                    "latency_ms": round(t_total, 2),
                    "tokens": tokens_used,
                    "cost_usd": cost_usd,
                    "timings": {
                        "route": route_time,
                        "retrieve": retrieve_time,
                        "rerank": rerank_time,
                        "generate": gen_time,
                    },
                }
                strat_results.append(q_res)
                all_question_results.append(q_res)

            # Compute Strategy Level Aggregate Metrics
            brier = compute_brier_score(strat_confidences, strat_correctness)
            ece, cal_bins = compute_ece_and_bins(strat_confidences, strat_correctness)
            p50_lat, p95_lat = compute_percentiles(strat_latencies_total)

            n_q = len(questions) or 1
            strat_kpis = StrategyMetrics(
                strategy=strat,
                hit_at_1=round(sum(hits_1) / n_q, 4),
                hit_at_3=round(sum(hits_3) / n_q, 4),
                hit_at_5=round(sum(hits_5) / n_q, 4),
                hit_at_10=round(sum(hits_10) / n_q, 4),
                precision_at_1=round(sum(prec_1) / n_q, 4),
                precision_at_3=round(sum(prec_3) / n_q, 4),
                precision_at_5=round(sum(prec_5) / n_q, 4),
                precision_at_10=round(sum(prec_10) / n_q, 4),
                recall_at_1=round(sum(rec_1) / n_q, 4),
                recall_at_3=round(sum(rec_3) / n_q, 4),
                recall_at_5=round(sum(rec_5) / n_q, 4),
                recall_at_10=round(sum(rec_10) / n_q, 4),
                mrr=round(sum(mrrs) / n_q, 4),
                ndcg_at_5=round(sum(ndcgs_5) / n_q, 4),
                ndcg_at_10=round(sum(ndcgs_10) / n_q, 4),
                symbol_recall_at_5=round(sum(symbol_recalls) / n_q, 4),
                intent_accuracy=round(sum(intent_accuracies) / n_q, 4),
                citation_validity=round(sum(cit_validities) / n_q, 4),
                citation_precision=round(sum(cit_precisions) / n_q, 4),
                citation_recall=round(sum(cit_recalls) / n_q, 4),
                must_mention_coverage=round(sum(must_mentions) / n_q, 4),
                answer_correctness=round(sum(answer_corrects) / n_q, 4),
                faithfulness=round(sum(cit_validities) / n_q, 4),
                latency_p50_ms=p50_lat,
                latency_p95_ms=p95_lat,
                total_tokens=sum(tokens_list),
                total_cost_usd=round(sum(costs_list), 5),
                avg_cost_usd=round(sum(costs_list) / n_q, 5),
                brier_score=brier,
                ece=ece,
                calibration_bins=[CalibrationBin(**b) for b in cal_bins],
            )
            strategy_metrics_map[strat] = strat_kpis

            # Latency breakdown per stage
            latency_breakdown_map[strat] = {
                "route_ms": round(sum(route_times) / n_q, 2),
                "retrieve_ms": round(sum(retrieve_times) / n_q, 2),
                "rerank_ms": round(sum(rerank_times) / n_q, 2),
                "generate_ms": round(sum(gen_times) / n_q, 2),
                "total_ms": p50_lat,
            }

            # Category Breakdown
            for q_r in strat_results:
                cat = q_r["category"]
                cat_data = category_breakdown_map.setdefault(
                    cat, {"count": 0, "hit_at_5": 0, "mrr_sum": 0.0, "correct_count": 0}
                )
                cat_data["count"] += 1
                if q_r["hit_at_5"]:
                    cat_data["hit_at_5"] += 1
                cat_data["mrr_sum"] += q_r["reciprocal_rank"]
                if q_r["answer_correct"]:
                    cat_data["correct_count"] += 1

        # Format category breakdown averages
        formatted_cat_breakdown: dict[str, dict[str, Any]] = {}
        for cat, data in category_breakdown_map.items():
            c_cnt = data["count"] or 1
            formatted_cat_breakdown[cat] = {
                "count": data["count"],
                "hit_rate": round(data["hit_at_5"] / c_cnt, 4),
                "mrr": round(data["mrr_sum"] / c_cnt, 4),
                "accuracy": round(data["correct_count"] / c_cnt, 4),
            }

        # Save question-level results and complete run
        await self.eval_repo.save_question_results(run_id, all_question_results)
        await self.eval_repo.complete_run(
            run_id,
            strategy_metrics={k: v.model_dump() for k, v in strategy_metrics_map.items()},
            latency_breakdown=latency_breakdown_map,
            category_breakdown=formatted_cat_breakdown,
        )

        return {
            "run_id": run_id,
            "status": "completed",
            "strategy_metrics": {k: v.model_dump() for k, v in strategy_metrics_map.items()},
            "latency_breakdown": latency_breakdown_map,
            "category_breakdown": formatted_cat_breakdown,
            "total_questions_evaluated": len(all_question_results),
        }
