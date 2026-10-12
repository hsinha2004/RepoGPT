"""
Unit tests for Phase 2: Diff Parser, Finding Validation, and Review Evaluator (§10).
"""

from __future__ import annotations

import pytest

from app.services.review.diff_parser import apply_patch_to_text, parse_unified_diff
from app.services.review.eval import ReviewEvaluator
from app.services.review.validator import ReviewValidator

SAMPLE_DIFF = """--- a/app/tasks.py
+++ b/app/tasks.py
@@ -3,3 +3,4 @@
 def get_task(task_id: int):
-    return db.query(task_id)
+    query = f"SELECT * FROM tasks WHERE id = {task_id}"
+    return db.execute(query)
"""

ORIGINAL_CONTENT = """import db

def get_task(task_id: int):
    return db.query(task_id)

def list_tasks():
    return db.all()
"""


def test_unified_diff_parser_and_patch_applier() -> None:
    diffs = parse_unified_diff(SAMPLE_DIFF)
    assert len(diffs) == 1
    fd = diffs[0]
    assert fd.path == "app/tasks.py"
    assert len(fd.hunks) == 1
    assert 4 in fd.changed_new_lines
    assert 5 in fd.changed_new_lines

    # Apply patch to original content
    head = apply_patch_to_text(ORIGINAL_CONTENT, fd)
    assert 'query = f"SELECT * FROM tasks WHERE id = {task_id}"' in head
    assert "return db.query(task_id)" not in head
    assert "def list_tasks():" in head


def test_review_validator_anchoring_and_deduplication() -> None:
    validator = ReviewValidator(min_confidence=0.7)

    raw_findings = [
        {
            "path": "app/tasks.py",
            "start_line": 11,
            "end_line": 12,
            "category": "security",
            "severity": "critical",
            "title": "SQL Injection",
            "explanation": "Unsanitized input.",
            "confidence": 0.95,
        },
        # Near duplicate on overlapping line
        {
            "path": "app/tasks.py",
            "start_line": 11,
            "end_line": 11,
            "category": "security",
            "severity": "critical",
            "title": "SQL Injection",
            "explanation": "Duplicate issue.",
            "confidence": 0.90,
        },
        # Unanchored finding outside changed hunks
        {
            "path": "app/tasks.py",
            "start_line": 85,
            "end_line": 86,
            "category": "maintainability",
            "severity": "low",
            "title": "Old function needs docstring",
            "explanation": "Missing docstring on line 85.",
            "confidence": 0.85,
        },
        # Low confidence finding
        {
            "path": "app/tasks.py",
            "start_line": 11,
            "end_line": 11,
            "category": "bug",
            "severity": "info",
            "title": "Weak hunch",
            "explanation": "Just guessing.",
            "confidence": 0.40,
        },
    ]

    file_changed_lines = {"app/tasks.py": {10, 11, 12}}

    findings, general_comments, risk_level, stats = validator.validate_and_rank(
        raw_findings=raw_findings,
        file_changed_lines=file_changed_lines,
    )

    # 1. Near duplicate should be removed
    assert len(findings) == 1
    assert findings[0]["title"] == "SQL Injection"
    assert findings[0]["severity"] == "critical"

    # 2. Unanchored finding moved to general_comments
    assert len(general_comments) == 1
    assert general_comments[0]["title"] == "Old function needs docstring"

    # 3. Risk level should be critical due to critical finding
    assert risk_level == "critical"
    assert stats["critical_count"] == 1


@pytest.mark.asyncio
async def test_seeded_patches_evaluation_suite() -> None:
    evaluator = ReviewEvaluator()
    metrics = await evaluator.evaluate_suite("eval/patches")

    assert metrics.patches_evaluated == 6
    assert metrics.total_seeded == 6
    assert metrics.matched_seeded == 6, (
        f"Expected 6/6 matched seeded issues, got {metrics.matched_seeded}"
    )
    assert metrics.detection_recall == 1.0, (
        f"Expected 100% detection recall, got {metrics.detection_recall}"
    )
    assert metrics.strict_recall >= 0.83, (
        f"Expected >= 83% strict recall, got {metrics.strict_recall}"
    )
    assert metrics.precision > 0.0
    assert metrics.localization_accuracy >= 0.80
