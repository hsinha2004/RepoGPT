from __future__ import annotations

import csv
import io
import json
from typing import Any


class EvalReportExporter:
    """Exports evaluation run metrics and results to Markdown, CSV, and JSON (§14.3)."""

    @staticmethod
    def to_markdown(run: dict[str, Any], question_results: list[dict[str, Any]]) -> str:
        """Generates a structured Markdown report with KPI comparison and breakdown tables."""
        run_id = run.get("id") or str(run.get("_id", ""))
        repo_name = run.get("repo_name", "Repository")
        benchmark_name = run.get("benchmark_name", "Benchmark")
        created_at = run.get("created_at", "")
        strategy_metrics = run.get("strategy_metrics", {})
        latency_breakdown = run.get("latency_breakdown", {})
        category_breakdown = run.get("category_breakdown", {})

        lines = [
            f"# RepoGPT Evaluation Report — {benchmark_name}",
            "",
            f"**Repository:** `{repo_name}`  ",
            f"**Run ID:** `{run_id}`  ",
            f"**Generated:** {created_at}  ",
            f"**Total Questions Evaluated:** {len(question_results)}  ",
            "",
            "---",
            "",
            "## 1. Strategy KPI Comparison",
            "",
            "| Strategy | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Precision@5 | Recall@5 | MRR | nDCG@10 | Cit. Prec | Cit. Recall | Accuracy | Latency p50 | ECE |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]

        for strat, m in strategy_metrics.items():
            lines.append(
                f"| **{strat}** | "
                f"{m.get('hit_at_1', 0):.2f} | "
                f"{m.get('hit_at_3', 0):.2f} | "
                f"{m.get('hit_at_5', 0):.2f} | "
                f"{m.get('hit_at_10', 0):.2f} | "
                f"{m.get('precision_at_5', 0):.2f} | "
                f"{m.get('recall_at_5', 0):.2f} | "
                f"{m.get('mrr', 0):.2f} | "
                f"{m.get('ndcg_at_10', 0):.2f} | "
                f"{m.get('citation_precision', 0):.2f} | "
                f"{m.get('citation_recall', 0):.2f} | "
                f"{m.get('answer_correctness', 0):.2f} | "
                f"{m.get('latency_p50_ms', 0):.0f} ms | "
                f"{m.get('ece', 0):.3f} |"
            )

        lines.extend(
            [
                "",
                "## 2. Latency Breakdown per Stage",
                "",
                "| Strategy | Route (ms) | Retrieve (ms) | Rerank (ms) | Generate (ms) | Total p50 (ms) |",
                "|---|---|---|---|---|---|",
            ]
        )

        for strat, lat in latency_breakdown.items():
            lines.append(
                f"| **{strat}** | "
                f"{lat.get('route_ms', 0):.1f} | "
                f"{lat.get('retrieve_ms', 0):.1f} | "
                f"{lat.get('rerank_ms', 0):.1f} | "
                f"{lat.get('generate_ms', 0):.1f} | "
                f"{lat.get('total_ms', 0):.0f} |"
            )

        if category_breakdown:
            lines.extend(
                [
                    "",
                    "## 3. Performance by Question Category",
                    "",
                    "| Category | Questions | Hit@5 Rate | MRR | Answer Accuracy |",
                    "|---|---|---|---|---|",
                ]
            )
            for cat, c_data in category_breakdown.items():
                lines.append(
                    f"| **{cat}** | "
                    f"{c_data.get('count', 0)} | "
                    f"{c_data.get('hit_rate', 0):.2f} | "
                    f"{c_data.get('mrr', 0):.2f} | "
                    f"{c_data.get('accuracy', 0):.2f} |"
                )

        lines.extend(
            [
                "",
                "## 4. Question-Level Drill-Down (Sample)",
                "",
                "| Q ID | Category | Strategy | Predicted Intent | Hit@5 | Citations | Correct | Latency |",
                "|---|---|---|---|---|---|---|---|",
            ]
        )

        for q in question_results[:20]:
            cits = ", ".join(q.get("citations", [])) or "None"
            hit_str = "✅" if q.get("hit_at_5") else "❌"
            corr_str = "✅" if q.get("answer_correct") else "❌"
            lines.append(
                f"| {q.get('question_id')} | {q.get('category')} | {q.get('strategy')} | "
                f"{q.get('predicted_intent')} | {hit_str} | {cits} | {corr_str} | {q.get('latency_ms', 0):.0f} ms |"
            )

        return "\n".join(lines)

    @staticmethod
    def to_csv(question_results: list[dict[str, Any]]) -> str:
        """Serializes question evaluation results to CSV."""
        if not question_results:
            return ""

        output = io.StringIO()
        fieldnames = [
            "question_id",
            "category",
            "strategy",
            "question",
            "expected_intent",
            "predicted_intent",
            "hit_at_5",
            "reciprocal_rank",
            "citation_valid",
            "citation_precision",
            "citation_recall",
            "must_mention_coverage",
            "answer_correct",
            "confidence",
            "latency_ms",
            "tokens",
            "cost_usd",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in question_results:
            writer.writerow(r)
        return output.getvalue()

    @staticmethod
    def to_json(run: dict[str, Any], question_results: list[dict[str, Any]]) -> str:
        """Serializes complete run and question results to formatted JSON."""
        combined = {
            "run": run,
            "results": question_results,
        }
        return json.dumps(combined, indent=2, default=str)
