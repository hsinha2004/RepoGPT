"""
Evaluation harness for Code Review against seeded patches (§10.6).
Calculates: detection recall, strict recall, precision, localization accuracy, and FP/100 lines.
"""

from __future__ import annotations

import os
import time
from typing import Any

import yaml

from app.agents.review_graph import ReviewGraphRunner, ReviewGraphState
from app.schemas.review import ReviewEvalMetrics
from app.services.review.diff_parser import parse_unified_diff


class ReviewEvaluator:
    """
    Evaluates automated code review against seeded ground-truth patches (§10.6).
    """

    def __init__(self, runner: ReviewGraphRunner | None = None) -> None:
        self.runner = runner or ReviewGraphRunner()

    async def evaluate_suite(self, patches_dir: str = "eval/patches") -> ReviewEvalMetrics:
        """
        Runs evaluation over all seeded patches defined in expected.yaml.
        """
        yaml_path = os.path.join(patches_dir, "expected.yaml")
        if not os.path.exists(yaml_path):
            alt_dir = os.path.join("..", patches_dir)
            alt_yaml = os.path.join(alt_dir, "expected.yaml")
            if os.path.exists(alt_yaml):
                patches_dir = alt_dir
                yaml_path = alt_yaml
            else:
                raise FileNotFoundError(f"Expected benchmark manifest not found at {yaml_path}")

        with open(yaml_path, encoding="utf-8") as yf:
            manifest = yaml.safe_load(yf)

        patches = manifest.get("patches", [])
        total_seeded = len(patches)
        matched_seeded = 0
        strict_matched = 0
        total_findings = 0
        total_changed_lines = 0
        localization_diffs: list[float] = []

        start_time = time.perf_counter()

        for p_info in patches:
            patch_file = os.path.join(patches_dir, p_info["file"])
            if not os.path.exists(patch_file):
                continue

            with open(patch_file, encoding="utf-8") as pf:
                diff_text = pf.read()

            parsed_diffs = parse_unified_diff(diff_text)
            diff_dicts: list[dict[str, Any]] = []
            for pd in parsed_diffs:
                total_changed_lines += pd.added_line_count + pd.deleted_line_count
                diff_dicts.append(
                    {
                        "path": pd.path,
                        "old_path": pd.old_path,
                        "is_added": pd.is_added,
                        "is_deleted": pd.is_deleted,
                        "is_modified": pd.is_modified,
                        "added_line_count": pd.added_line_count,
                        "deleted_line_count": pd.deleted_line_count,
                        "changed_new_lines": pd.changed_new_lines,
                        "hunks": [
                            {
                                "old_start": h.old_start,
                                "old_length": h.old_length,
                                "new_start": h.new_start,
                                "new_length": h.new_length,
                                "raw_lines": h.raw_lines,
                                "added_lines": h.added_lines,
                                "deleted_lines": h.deleted_lines,
                            }
                            for h in pd.hunks
                        ],
                    }
                )

            # Run review graph on this patch
            state: ReviewGraphState = {
                "repo_id": "test_repo",
                "pr_title": f"Patch {p_info['id']}: {p_info['title']}",
                "pr_description": p_info["description"],
                "file_diffs": diff_dicts,
                "file_contexts": {},
                "file_symbols": {},
                "static_analysis_results": {},
            }

            result_state = await self.runner.run(state)
            findings = result_state.get("validated_findings", [])
            total_findings += len(findings)

            # Match against expected seeded finding
            target_file = p_info["target_file"]
            exp_start = p_info["start_line"]
            exp_end = p_info["end_line"]
            exp_category = p_info["category"]

            is_detected = False
            is_strict = False

            for finding in findings:
                # Same file check
                if finding["path"] == target_file:
                    # Line overlap within ±3 lines (§10.6)
                    f_start = finding["start_line"]
                    f_end = finding["end_line"]
                    overlap = not (f_end < exp_start - 3 or f_start > exp_end + 3)

                    if overlap:
                        is_detected = True
                        loc_error = abs(f_start - exp_start)
                        localization_diffs.append(loc_error)

                        if finding["category"] == exp_category:
                            is_strict = True
                        break

            if is_detected:
                matched_seeded += 1
            if is_strict:
                strict_matched += 1

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        detection_recall = round(matched_seeded / total_seeded, 4) if total_seeded > 0 else 0.0
        strict_recall = round(strict_matched / total_seeded, 4) if total_seeded > 0 else 0.0
        precision = round(matched_seeded / total_findings, 4) if total_findings > 0 else 0.0
        avg_loc_accuracy = (
            round(sum(1 for d in localization_diffs if d <= 3) / len(localization_diffs), 4)
            if localization_diffs
            else 1.0
        )
        fp_count = max(0, total_findings - matched_seeded)
        fp_per_100 = round((fp_count / max(1, total_changed_lines)) * 100, 2)

        return ReviewEvalMetrics(
            detection_recall=detection_recall,
            strict_recall=strict_recall,
            precision=precision,
            localization_accuracy=avg_loc_accuracy,
            false_positives_per_100_lines=fp_per_100,
            total_seeded=total_seeded,
            matched_seeded=matched_seeded,
            total_findings=total_findings,
            latency_ms=elapsed_ms,
            cost_usd=0.0,
            patches_evaluated=total_seeded,
        )
