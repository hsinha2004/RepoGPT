from __future__ import annotations

from typing import Any

import pytest

from app.core.config import Settings
from app.db.repositories.benchmarks import BenchmarkRepository
from app.db.repositories.eval_runs import EvalRunRepository
from app.db.repositories.repos import RepositoryRepository
from app.schemas.retrieval import RetrievedChunk, RouteResult, SearchRequest, SearchResponse
from app.services.eval.report import EvalReportExporter
from app.services.eval.runner import EvaluationRunner
from app.services.llm.fake import FakeProvider


class MockEvalRunsCollection:
    def __init__(self) -> None:
        self.runs: dict[str, dict[str, Any]] = {}

    async def insert_one(self, doc: dict[str, Any]) -> Any:
        oid = f"run_{len(self.runs) + 1}"
        doc["_id"] = oid
        self.runs[oid] = dict(doc)
        return type("Res", (), {"inserted_id": oid})()

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        rid = str(query.get("_id") or query.get("id"))
        return self.runs.get(rid)

    def find(self, query: dict[str, Any]) -> Any:
        items = list(self.runs.values())

        class MockCursor:
            def sort(self, *args: Any) -> MockCursor:
                _ = args
                return self

            def limit(self, *args: Any) -> MockCursor:
                _ = args
                return self

            async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
                _ = length
                return items

        return MockCursor()

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> Any:
        rid = str(query.get("_id") or query.get("id"))
        if rid in self.runs and "$set" in update:
            self.runs[rid].update(update["$set"])
        return type("Res", (), {"modified_count": 1})()


class MockEvalResultsCollection:
    def __init__(self) -> None:
        self.results: dict[str, list[dict[str, Any]]] = {}

    async def insert_many(self, docs: list[dict[str, Any]]) -> Any:
        for d in docs:
            rid = d.get("run_id", "")
            d["_id"] = f"res_{len(self.results.setdefault(rid, [])) + 1}"
            self.results[rid].append(d)
        return type("Res", (), {"inserted_ids": [d["_id"] for d in docs]})()

    def find(self, query: dict[str, Any]) -> Any:
        rid = query.get("run_id", "")
        items = self.results.get(rid, [])

        class MockCursor:
            async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
                _ = length
                return list(items)

        return MockCursor()


class MockRetrievalService:
    def __init__(self) -> None:
        pass

    async def search(self, repo_id: str, request: SearchRequest) -> SearchResponse:
        _ = repo_id
        # Return canned relevant chunks matching sample questions
        chunks = [
            RetrievedChunk(
                chunk_id="c1",
                path="backend/app/auth/security.py",
                text="def create_access_token(data, expire): return 'token'",
                score=0.92,
                chunk_type="function",
                start_line=10,
                end_line=25,
            ),
            RetrievedChunk(
                chunk_id="c2",
                path="backend/app/auth/routes.py",
                text="def login(): return create_access_token()",
                score=0.81,
                chunk_type="function",
                start_line=30,
                end_line=45,
            ),
        ]
        route = RouteResult(
            intent="locate",
            strategy=request.strategy or "hybrid_rerank",
            reason="Mock search route",
        )
        return SearchResponse(
            query=request.query,
            strategy=request.strategy or "hybrid_rerank",
            route=route,
            chunks=chunks,
            total_candidates=2,
            timings={"route": 5.0, "retrieve": 12.0, "rerank": 4.0},
        )


@pytest.mark.asyncio
async def test_evaluation_runner_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        DATA_DIR=".",
        LLM_PROVIDER="fake",
        LLM_MODEL="fake-model",
    )

    mock_runs_col = MockEvalRunsCollection()
    mock_results_col = MockEvalResultsCollection()
    eval_repo = EvalRunRepository(
        runs_collection=mock_runs_col,  # type: ignore[arg-type]
        results_collection=mock_results_col,  # type: ignore[arg-type]
    )
    benchmark_repo = BenchmarkRepository()
    mock_retrieval = MockRetrievalService()
    fake_llm = FakeProvider()

    # 1. Verify Built-in Benchmarks
    benchmarks = await benchmark_repo.list_benchmarks()
    assert len(benchmarks) >= 1
    sample_b = next((b for b in benchmarks if "sample" in b.get("name", "").lower()), benchmarks[0])
    b_id = sample_b["id"]

    # 2. Test Estimation
    runner = EvaluationRunner(
        settings=settings,
        eval_repo=eval_repo,
        benchmark_repo=benchmark_repo,
        retrieval_service=mock_retrieval,  # type: ignore[arg-type]
        llm=fake_llm,
    )

    estimate = runner.estimate_run(
        benchmark=sample_b,
        strategies=["keyword", "hybrid_rerank"],
        generate_answers=True,
    )
    assert estimate.question_count > 0
    assert estimate.strategies_count == 2
    assert estimate.estimated_llm_calls > 0
    assert estimate.estimated_cost_usd >= 0.0

    # 3. Create and Execute an Evaluation Run (subset of 3 questions for speed)
    test_benchmark = {
        "id": "b_test",
        "name": "Quick Test Benchmark",
        "questions": sample_b.get("questions", [])[:3],
    }

    async def mock_get_benchmark(_bid: str) -> dict[str, Any]:
        return test_benchmark

    monkeypatch.setattr(benchmark_repo, "get_benchmark", mock_get_benchmark)

    run_doc = await eval_repo.create_run(
        repo_id="test_repo_1",
        benchmark_id="b_test",
        user_id="test_user_1",
        strategies=["hybrid_rerank"],
        generate_answers=True,
    )
    run_id = str(run_doc["id"])

    res = await runner.run_evaluation(
        run_id=run_id,
        repo_id="test_repo_1",
        benchmark_id="b_test",
        strategies=["hybrid_rerank"],
        generate_answers=True,
    )

    assert res["status"] == "completed"
    assert "hybrid_rerank" in res["strategy_metrics"]
    metrics = res["strategy_metrics"]["hybrid_rerank"]
    assert "hit_at_5" in metrics
    assert "mrr" in metrics
    assert "brier_score" in metrics
    assert "ece" in metrics
    assert len(metrics["calibration_bins"]) == 10

    # 4. Verify Results Persistence
    q_results = await eval_repo.get_results_for_run(run_id)
    assert len(q_results) == 3

    # 5. Verify Exporters
    completed_run = await eval_repo.get_run(run_id)
    assert completed_run is not None

    md_export = EvalReportExporter.to_markdown(completed_run, q_results)
    assert "# RepoGPT Evaluation Report" in md_export
    assert "Strategy KPI Comparison" in md_export

    csv_export = EvalReportExporter.to_csv(q_results)
    assert "question_id,category,strategy" in csv_export
    assert len(csv_export.splitlines()) == 4  # Header + 3 rows

    json_export = EvalReportExporter.to_json(completed_run, q_results)
    assert '"run":' in json_export
    assert '"results":' in json_export
