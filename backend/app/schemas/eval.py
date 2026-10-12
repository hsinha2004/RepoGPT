from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BenchmarkRepo(BaseModel):
    """Repository specification for a benchmark."""

    type: str = "fixture"  # fixture | github
    path: str | None = None
    url: str | None = None
    ref: str | None = None


class BenchmarkQuestion(BaseModel):
    """Ground-truth question in an evaluation benchmark (§14.1)."""

    id: str
    question: str
    category: str = "locate"  # locate | explain | flow | architecture | dependency | config
    expected_intent: str = "locate"
    expected_files: list[str] = Field(default_factory=list)
    expected_symbols: list[str] = Field(default_factory=list)
    must_mention: list[str] = Field(default_factory=list)
    reference_answer: str = ""


class Benchmark(BaseModel):
    """Benchmark schema representing a dataset of ground-truth questions."""

    id: str
    name: str
    description: str = ""
    repo: BenchmarkRepo
    questions: list[BenchmarkQuestion] = Field(default_factory=list)
    question_count: int = 0
    is_builtin: bool = False
    created_at: str | None = None
    owner_id: str | None = None


class BenchmarkCreate(BaseModel):
    """Payload for uploading or creating a benchmark."""

    name: str
    description: str = ""
    repo: BenchmarkRepo
    questions: list[BenchmarkQuestion]


class EvalEstimateRequest(BaseModel):
    """Pre-flight evaluation resource estimate request."""

    benchmark_id: str
    strategies: list[str] = Field(default_factory=lambda: ["hybrid_rerank"])
    generate_answers: bool = True
    llm_judge: bool = False
    k_values: list[int] = Field(default_factory=lambda: [1, 3, 5, 10])


class EvalEstimateResponse(BaseModel):
    """Resource estimation for an evaluation run."""

    estimated_llm_calls: int
    estimated_tokens: int
    estimated_cost_usd: float
    estimated_duration_seconds: float
    question_count: int
    strategies_count: int


class EvalRunCreate(BaseModel):
    """Configuration to start a new evaluation run."""

    repo_id: str
    benchmark_id: str
    strategies: list[str] = Field(
        default_factory=lambda: ["keyword", "vector", "hybrid", "hybrid_rerank", "auto"]
    )
    router_mode: str = "hybrid"  # heuristic | llm | hybrid
    k_values: list[int] = Field(default_factory=lambda: [1, 3, 5, 10])
    generate_answers: bool = True
    llm_judge: bool = False
    vector_store: str = "chroma"  # chroma | faiss
    embedding_model: str | None = None


class CalibrationBin(BaseModel):
    """Calibration bin for reliability diagram."""

    bin_center: float
    confidence_avg: float
    accuracy: float
    count: int


class StrategyMetrics(BaseModel):
    """Computed metrics for one strategy in an evaluation run (§14.2)."""

    strategy: str
    hit_at_1: float = 0.0
    hit_at_3: float = 0.0
    hit_at_5: float = 0.0
    hit_at_10: float = 0.0
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    symbol_recall_at_5: float = 0.0
    intent_accuracy: float = 0.0
    citation_validity: float = 0.0
    citation_precision: float = 0.0
    citation_recall: float = 0.0
    must_mention_coverage: float = 0.0
    answer_correctness: float = 0.0
    faithfulness: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_cost_usd: float = 0.0
    brier_score: float = 0.0
    ece: float = 0.0
    calibration_bins: list[CalibrationBin] = Field(default_factory=list)


class EvalRunSummary(BaseModel):
    """Full summary of an evaluation run including aggregate metrics."""

    id: str
    repo_id: str
    repo_name: str = ""
    benchmark_id: str
    benchmark_name: str = ""
    status: str = "queued"  # queued | running | completed | failed | cancelled
    progress: int = 0
    current_stage: str = ""
    strategies: list[str] = Field(default_factory=list)
    k_values: list[int] = Field(default_factory=lambda: [1, 3, 5, 10])
    generate_answers: bool = True
    llm_judge: bool = False
    vector_store: str = "chroma"
    embedding_model: str | None = None
    created_at: str
    completed_at: str | None = None
    error: str | None = None
    strategy_metrics: dict[str, StrategyMetrics] = Field(default_factory=dict)
    latency_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)
    category_breakdown: dict[str, dict[str, Any]] = Field(default_factory=dict)


class EvalQuestionResult(BaseModel):
    """Detailed result for an individual question/strategy run."""

    id: str | None = None
    run_id: str
    question_id: str
    question: str
    category: str
    expected_intent: str
    expected_files: list[str]
    expected_symbols: list[str] = Field(default_factory=list)
    strategy: str
    predicted_intent: str
    retrieved_files: list[str] = Field(default_factory=list)
    hit_at_5: bool = False
    reciprocal_rank: float = 0.0
    generated_answer: str | None = None
    citations: list[str] = Field(default_factory=list)
    confidence: float | None = None
    citation_valid: bool = False
    citation_precision: float = 0.0
    citation_recall: float = 0.0
    must_mention_coverage: float = 0.0
    answer_correct: bool = False
    latency_ms: float = 0.0
    tokens: int = 0
    cost_usd: float = 0.0
    timings: dict[str, float] = Field(default_factory=dict)


class EvalLiveMetrics(BaseModel):
    """Aggregated live metrics from user chats."""

    questions_per_day: list[dict[str, Any]] = Field(default_factory=list)
    latency_p50_p95: list[dict[str, Any]] = Field(default_factory=list)
    tokens_and_cost: list[dict[str, Any]] = Field(default_factory=list)
    feedback_satisfaction_ratio: float = 0.0
    total_feedback_count: int = 0
    confidence_distribution: list[dict[str, Any]] = Field(default_factory=list)
