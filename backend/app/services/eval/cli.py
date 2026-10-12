from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings
from app.db.repositories.benchmarks import BenchmarkRepository
from app.db.repositories.eval_runs import EvalRunRepository
from app.db.repositories.repos import RepositoryRepository
from app.services.eval.report import EvalReportExporter
from app.services.eval.runner import EvaluationRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RepoGPT Evaluation Runner CLI (§14.3)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run benchmark evaluation")
    run_parser.add_argument(
        "--benchmark",
        type=str,
        default="eval/benchmarks/sample_repo.yaml",
        help="Path to benchmark YAML/JSON file",
    )
    run_parser.add_argument(
        "--strategies",
        type=str,
        default="all",
        help="Comma-separated strategies or 'all' (keyword,vector,hybrid,hybrid_rerank,auto)",
    )
    run_parser.add_argument(
        "--generate",
        action="store_true",
        default=True,
        help="Generate answers and evaluate citations/correctness",
    )
    run_parser.add_argument(
        "--no-generate",
        dest="generate",
        action="store_false",
        help="Evaluate retrieval only without generating answers",
    )
    run_parser.add_argument(
        "--repo-id",
        type=str,
        default=None,
        help="Target repository ID (auto-detected if omitted)",
    )
    run_parser.add_argument(
        "--out",
        type=str,
        default="results/",
        help="Output directory for reports and results",
    )
    return parser.parse_args()


async def execute_cli(args: argparse.Namespace) -> None:
    settings = get_settings()
    benchmark_path = Path(args.benchmark)
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark file {args.benchmark} not found.")

    with open(benchmark_path, encoding="utf-8") as f:
        benchmark_data: dict[str, Any] = yaml.safe_load(f)

    # Determine strategies
    if args.strategies == "all":
        strategies = ["keyword", "vector", "hybrid", "hybrid_rerank", "auto"]
    else:
        strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]

    # Find repo
    repo_id = args.repo_id or "sample_repo"

    eval_repo = EvalRunRepository()
    benchmark_repo = BenchmarkRepository()

    b_id = f"builtin:{benchmark_data.get('name', 'benchmark')}"
    run_doc = await eval_repo.create_run(
        repo_id=repo_id,
        benchmark_id=b_id,
        user_id="cli_user",
        benchmark_name=benchmark_data.get("name", "Benchmark"),
        strategies=strategies,
        generate_answers=args.generate,
    )
    run_id = str(run_doc["id"])

    repo_repo = RepositoryRepository()
    runner = EvaluationRunner(
        settings=settings,
        eval_repo=eval_repo,
        benchmark_repo=benchmark_repo,
        repo_repo=repo_repo,
    )

    print(f"Starting evaluation run {run_id} on {benchmark_data.get('name')}...")
    print(f"Strategies: {', '.join(strategies)} | Generate answers: {args.generate}")

    res = await runner.run_evaluation(
        run_id=run_id,
        repo_id=repo_id,
        benchmark_id=b_id,
        strategies=strategies,
        generate_answers=args.generate,
    )

    completed_run = await eval_repo.get_run(run_id) or run_doc
    q_results = await eval_repo.get_results_for_run(run_id)

    # Export results
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_report = EvalReportExporter.to_markdown(completed_run, q_results)
    csv_report = EvalReportExporter.to_csv(q_results)
    json_report = EvalReportExporter.to_json(completed_run, q_results)

    with open(out_dir / "report.md", "w", encoding="utf-8") as f:
        f.write(md_report)
    with open(out_dir / "results.csv", "w", encoding="utf-8") as f:
        f.write(csv_report)
    with open(out_dir / "results.json", "w", encoding="utf-8") as f:
        f.write(json_report)

    print(f"\nEvaluation finished! Reports generated in {out_dir.resolve()}/")
    print("\nStrategy Summary:")
    for strat, m in res.get("strategy_metrics", {}).items():
        print(
            f"  [{strat:14}] Hit@5: {m.get('hit_at_5', 0):.2f} | "
            f"MRR: {m.get('mrr', 0):.2f} | "
            f"nDCG@10: {m.get('ndcg_at_10', 0):.2f} | "
            f"Accuracy: {m.get('answer_correctness', 0):.2f} | "
            f"p50: {m.get('latency_p50_ms', 0):.0f}ms"
        )


def main() -> None:
    args = parse_args()
    if args.command == "run":
        asyncio.run(execute_cli(args))


if __name__ == "__main__":
    main()
