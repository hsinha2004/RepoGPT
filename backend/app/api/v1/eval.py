"""Evaluation endpoints (§13.4, §14).

Supports benchmark management, pre-flight estimation, evaluation run execution,
metrics inspection, comparison, and exporting.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
import yaml
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.errors import NotFoundError, ValidationFailedError
from app.db.repositories.benchmarks import BenchmarkRepository
from app.db.repositories.eval_runs import EvalRunRepository
from app.db.repositories.repos import RepositoryRepository
from app.schemas.eval import (
    Benchmark,
    BenchmarkCreate,
    EvalEstimateRequest,
    EvalEstimateResponse,
    EvalLiveMetrics,
    EvalQuestionResult,
    EvalRunCreate,
    EvalRunSummary,
)
from app.schemas.review import ReviewEvalMetrics
from app.services.eval.report import EvalReportExporter
from app.services.eval.runner import EvaluationRunner

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/eval", tags=["evaluation"])


def get_eval_runner() -> EvaluationRunner:
    return EvaluationRunner(settings=get_settings())


def get_benchmark_repo() -> BenchmarkRepository:
    return BenchmarkRepository()


def get_eval_repo() -> EvalRunRepository:
    return EvalRunRepository()


def get_repo_repo() -> RepositoryRepository:
    return RepositoryRepository()


# -----------------------------------------------------------------------------
# 1. Benchmarks
# -----------------------------------------------------------------------------


@router.get("/benchmarks", response_model=list[Benchmark])
async def list_benchmarks(
    current_user: dict[str, Any] = Depends(get_current_user),
    benchmark_repo: BenchmarkRepository = Depends(get_benchmark_repo),
) -> list[dict[str, Any]]:
    """Lists built-in and user-uploaded evaluation benchmarks."""
    user_id = str(current_user["_id"])
    return await benchmark_repo.list_benchmarks(owner_id=user_id)


@router.get("/benchmarks/{benchmark_id}", response_model=Benchmark)
async def get_benchmark_detail(
    benchmark_id: str,
    _current_user: dict[str, Any] = Depends(get_current_user),
    benchmark_repo: BenchmarkRepository = Depends(get_benchmark_repo),
) -> dict[str, Any]:
    """Retrieves full details and questions for a benchmark."""
    doc = await benchmark_repo.get_benchmark(benchmark_id)
    if not doc:
        raise NotFoundError(f"Benchmark '{benchmark_id}' not found.")
    return doc


@router.post("/benchmarks", response_model=Benchmark, status_code=status.HTTP_201_CREATED)
async def upload_benchmark(
    file: UploadFile | None = File(None),
    current_user: dict[str, Any] = Depends(get_current_user),
    benchmark_repo: BenchmarkRepository = Depends(get_benchmark_repo),
) -> dict[str, Any]:
    """Uploads a benchmark file in YAML or JSON format (§14.1)."""
    if file is None:
        raise ValidationFailedError("A benchmark YAML or JSON file must be uploaded.")

    content_bytes = await file.read()
    try:
        raw_data = yaml.safe_load(content_bytes.decode("utf-8"))
        if not isinstance(raw_data, dict):
            raise ValueError("YAML content must be a dictionary.")
    except Exception as e:
        raise ValidationFailedError(f"Invalid benchmark YAML/JSON: {e}") from e

    try:
        parsed = BenchmarkCreate(**raw_data)
    except Exception as e:
        raise ValidationFailedError(f"Benchmark schema validation failed: {e}") from e

    user_id = str(current_user["_id"])
    doc = await benchmark_repo.create_benchmark(
        name=parsed.name,
        description=parsed.description,
        repo=parsed.repo.model_dump(),
        questions=[q.model_dump() for q in parsed.questions],
        owner_id=user_id,
    )
    return doc


@router.delete("/benchmarks/{benchmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_benchmark(
    benchmark_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    benchmark_repo: BenchmarkRepository = Depends(get_benchmark_repo),
) -> None:
    """Deletes a custom uploaded benchmark."""
    user_id = str(current_user["_id"])
    if benchmark_id.startswith("builtin:"):
        raise ValidationFailedError("Built-in benchmarks cannot be deleted.")

    deleted = await benchmark_repo.delete_benchmark(benchmark_id, owner_id=user_id)
    if not deleted:
        raise NotFoundError("Benchmark not found or not owned by you.")


# -----------------------------------------------------------------------------
# 2. Pre-flight Estimation & Execution
# -----------------------------------------------------------------------------


@router.post("/estimate", response_model=EvalEstimateResponse)
async def estimate_evaluation(
    payload: EvalEstimateRequest,
    _current_user: dict[str, Any] = Depends(get_current_user),
    benchmark_repo: BenchmarkRepository = Depends(get_benchmark_repo),
    runner: EvaluationRunner = Depends(get_eval_runner),
) -> EvalEstimateResponse:
    """Calculates pre-flight LLM calls, tokens, cost, and duration estimate (§14.3)."""
    benchmark = await benchmark_repo.get_benchmark(payload.benchmark_id)
    if not benchmark:
        raise NotFoundError(f"Benchmark '{payload.benchmark_id}' not found.")

    return runner.estimate_run(
        benchmark=benchmark,
        strategies=payload.strategies,
        generate_answers=payload.generate_answers,
        llm_judge=payload.llm_judge,
    )


@router.post("/runs", response_model=EvalRunSummary, status_code=status.HTTP_202_ACCEPTED)
async def create_eval_run(
    payload: EvalRunCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    eval_repo: EvalRunRepository = Depends(get_eval_repo),
    benchmark_repo: BenchmarkRepository = Depends(get_benchmark_repo),
    repo_repo: RepositoryRepository = Depends(get_repo_repo),
    runner: EvaluationRunner = Depends(get_eval_runner),
) -> dict[str, Any]:
    """Creates and starts an evaluation run across strategies (§14.3)."""
    repo = await repo_repo.get_by_id(payload.repo_id)
    if not repo:
        raise NotFoundError(f"Repository '{payload.repo_id}' not found.")

    benchmark = await benchmark_repo.get_benchmark(payload.benchmark_id)
    if not benchmark:
        raise NotFoundError(f"Benchmark '{payload.benchmark_id}' not found.")

    user_id = str(current_user["_id"])
    repo_name = repo.get("name") or repo.get("display_name", "Repository")
    benchmark_name = benchmark.get("name", "Benchmark")

    run_doc = await eval_repo.create_run(
        repo_id=payload.repo_id,
        benchmark_id=payload.benchmark_id,
        user_id=user_id,
        repo_name=repo_name,
        benchmark_name=benchmark_name,
        strategies=payload.strategies,
        router_mode=payload.router_mode,
        k_values=payload.k_values,
        generate_answers=payload.generate_answers,
        llm_judge=payload.llm_judge,
        vector_store=payload.vector_store,
        embedding_model=payload.embedding_model,
    )

    run_id = str(run_doc["id"])

    # Launch evaluation asynchronously
    async def _run_bg() -> None:
        try:
            await runner.run_evaluation(
                run_id=run_id,
                repo_id=payload.repo_id,
                benchmark_id=payload.benchmark_id,
                strategies=payload.strategies,
                router_mode=payload.router_mode,
                k_values=payload.k_values,
                generate_answers=payload.generate_answers,
                llm_judge=payload.llm_judge,
                vector_store=payload.vector_store,
                embedding_model=payload.embedding_model,
            )
        except Exception as e:
            logger.error("background_eval_run_failed", run_id=run_id, error=str(e))
            await eval_repo.fail_run(run_id, str(e))

    asyncio.create_task(_run_bg())

    return run_doc


@router.get("/runs", response_model=list[EvalRunSummary])
async def list_eval_runs(
    repo_id: str | None = Query(None),
    current_user: dict[str, Any] = Depends(get_current_user),
    eval_repo: EvalRunRepository = Depends(get_eval_repo),
) -> list[dict[str, Any]]:
    """Lists past evaluation runs."""
    user_id = str(current_user["_id"])
    return await eval_repo.list_runs(repo_id=repo_id, user_id=user_id)


@router.get("/runs/{run_id}", response_model=EvalRunSummary)
async def get_eval_run_detail(
    run_id: str,
    _current_user: dict[str, Any] = Depends(get_current_user),
    eval_repo: EvalRunRepository = Depends(get_eval_repo),
) -> dict[str, Any]:
    """Retrieves status and aggregate metrics of an evaluation run."""
    run = await eval_repo.get_run(run_id)
    if not run:
        raise NotFoundError(f"Evaluation run '{run_id}' not found.")
    return run


@router.get("/runs/{run_id}/results", response_model=list[EvalQuestionResult])
async def get_eval_run_results(
    run_id: str,
    _current_user: dict[str, Any] = Depends(get_current_user),
    eval_repo: EvalRunRepository = Depends(get_eval_repo),
) -> list[dict[str, Any]]:
    """Retrieves per-question evaluation drill-down results."""
    run = await eval_repo.get_run(run_id)
    if not run:
        raise NotFoundError(f"Evaluation run '{run_id}' not found.")
    return await eval_repo.get_results_for_run(run_id)


@router.get("/runs/{run_id}/export")
async def export_eval_run(
    run_id: str,
    format: str = Query("json", pattern="^(json|csv|md|markdown)$"),
    _current_user: dict[str, Any] = Depends(get_current_user),
    eval_repo: EvalRunRepository = Depends(get_eval_repo),
) -> Response:
    """Exports evaluation run data as JSON, CSV, or Markdown (§14.3)."""
    run = await eval_repo.get_run(run_id)
    if not run:
        raise NotFoundError(f"Evaluation run '{run_id}' not found.")
    results = await eval_repo.get_results_for_run(run_id)

    if format == "csv":
        csv_data = EvalReportExporter.to_csv(results)
        return PlainTextResponse(
            csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="eval_run_{run_id}.csv"'},
        )
    elif format in ("md", "markdown"):
        md_data = EvalReportExporter.to_markdown(run, results)
        return PlainTextResponse(
            md_data,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="eval_run_{run_id}.md"'},
        )
    else:
        json_data = EvalReportExporter.to_json(run, results)
        return PlainTextResponse(
            json_data,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="eval_run_{run_id}.json"'},
        )


@router.get("/compare")
async def compare_runs(
    run_a: str = Query(...),
    run_b: str = Query(...),
    _current_user: dict[str, Any] = Depends(get_current_user),
    eval_repo: EvalRunRepository = Depends(get_eval_repo),
) -> dict[str, Any]:
    """Computes comparison deltas between two evaluation runs."""
    doc_a = await eval_repo.get_run(run_a)
    if not doc_a:
        raise NotFoundError(f"Run {run_a} not found.")

    doc_b = await eval_repo.get_run(run_b)
    if not doc_b:
        raise NotFoundError(f"Run {run_b} not found.")

    metrics_a = doc_a.get("strategy_metrics", {})
    metrics_b = doc_b.get("strategy_metrics", {})

    all_strats = sorted(set(metrics_a.keys()) | set(metrics_b.keys()))
    comparison: dict[str, dict[str, Any]] = {}

    for s in all_strats:
        sa = metrics_a.get(s, {})
        sb = metrics_b.get(s, {})
        comparison[s] = {
            "hit_at_5": {
                "run_a": sa.get("hit_at_5", 0.0),
                "run_b": sb.get("hit_at_5", 0.0),
                "delta": round(sb.get("hit_at_5", 0.0) - sa.get("hit_at_5", 0.0), 4),
            },
            "mrr": {
                "run_a": sa.get("mrr", 0.0),
                "run_b": sb.get("mrr", 0.0),
                "delta": round(sb.get("mrr", 0.0) - sa.get("mrr", 0.0), 4),
            },
            "ndcg_at_10": {
                "run_a": sa.get("ndcg_at_10", 0.0),
                "run_b": sb.get("ndcg_at_10", 0.0),
                "delta": round(sb.get("ndcg_at_10", 0.0) - sa.get("ndcg_at_10", 0.0), 4),
            },
            "answer_correctness": {
                "run_a": sa.get("answer_correctness", 0.0),
                "run_b": sb.get("answer_correctness", 0.0),
                "delta": round(
                    sb.get("answer_correctness", 0.0) - sa.get("answer_correctness", 0.0), 4
                ),
            },
            "latency_p50_ms": {
                "run_a": sa.get("latency_p50_ms", 0.0),
                "run_b": sb.get("latency_p50_ms", 0.0),
                "delta": round(sb.get("latency_p50_ms", 0.0) - sa.get("latency_p50_ms", 0.0), 2),
            },
        }

    return {
        "run_a": {"id": run_a, "name": doc_a.get("benchmark_name")},
        "run_b": {"id": run_b, "name": doc_b.get("benchmark_name")},
        "deltas": comparison,
    }


@router.get("/live", response_model=EvalLiveMetrics)
async def get_live_eval_metrics(
    _current_user: dict[str, Any] = Depends(get_current_user),
    eval_repo: EvalRunRepository = Depends(get_eval_repo),
) -> dict[str, Any]:
    """Returns telemetry and satisfaction rates from production chat usage (§14.2)."""
    return await eval_repo.get_live_metrics()


@router.get("/reviews", response_model=ReviewEvalMetrics)
async def get_review_eval_metrics(
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> ReviewEvalMetrics:
    """Evaluates automated code review against seeded patches (§10.6)."""
    from app.services.review.eval import ReviewEvaluator

    evaluator = ReviewEvaluator()
    return await evaluator.evaluate_suite()
