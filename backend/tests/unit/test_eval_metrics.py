from __future__ import annotations

import pytest

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


def test_hit_at_k_metrics():
    retrieved = ["src/a.py", "src/b.py", "src/c.py"]
    expected = ["src/b.py"]

    assert compute_hit_at_k(retrieved, expected, k=1) == 0.0
    assert compute_hit_at_k(retrieved, expected, k=2) == 1.0
    assert compute_hit_at_k(retrieved, expected, k=5) == 1.0
    assert compute_hit_at_k([], expected, k=1) == 0.0
    assert compute_hit_at_k(retrieved, [], k=1) == 0.0


def test_precision_and_recall_at_k():
    retrieved = ["src/a.py", "src/a.py", "src/b.py", "src/c.py"]
    expected = ["src/b.py", "src/c.py", "src/d.py"]

    # Unique top-2 are ["src/a.py", "src/b.py"]. Hits = 1 ("src/b.py"). Precision@2 = 1/2 = 0.5
    assert compute_precision_at_k(retrieved, expected, k=2) == 0.5
    # Unique top-3 are ["src/a.py", "src/b.py", "src/c.py"]. Hits = 2. Precision@3 = 2/3 ≈ 0.6667
    assert pytest.approx(compute_precision_at_k(retrieved, expected, k=3), 0.001) == 2 / 3

    # Recall: expected has 3 items. At k=2, 1 hit -> 1/3
    assert pytest.approx(compute_recall_at_k(retrieved, expected, k=2), 0.001) == 1 / 3
    # At k=3, 2 hits -> 2/3
    assert pytest.approx(compute_recall_at_k(retrieved, expected, k=3), 0.001) == 2 / 3
    # If expected is empty, recall is 1.0
    assert compute_recall_at_k(retrieved, [], k=2) == 1.0


def test_mrr_metric():
    retrieved = ["src/a.py", "src/b.py", "src/c.py"]
    assert compute_mrr(retrieved, ["src/a.py"]) == 1.0
    assert compute_mrr(retrieved, ["src/b.py"]) == 0.5
    assert pytest.approx(compute_mrr(retrieved, ["src/c.py"]), 0.001) == 1 / 3
    assert compute_mrr(retrieved, ["src/z.py"]) == 0.0
    assert compute_mrr([], ["src/a.py"]) == 0.0


def test_ndcg_at_k_graded():
    # item 1 has file + symbol (rel=2)
    # item 2 has file only (rel=1)
    # item 3 has nothing (rel=0)
    items_perfect = [
        {"path": "src/auth.py", "text": "def login(): pass"},
        {"path": "src/auth.py", "text": "import os"},
        {"path": "src/other.py", "text": "def foo(): pass"},
    ]
    expected_files = ["src/auth.py"]
    expected_symbols = ["login"]

    # When ranked optimally: nDCG should be 1.0
    score_perfect = compute_ndcg_at_k(items_perfect, expected_files, expected_symbols, k=3)
    assert pytest.approx(score_perfect, 0.001) == 1.0

    # Inverted order: rel=1 first, rel=2 second
    items_suboptimal = [
        {"path": "src/auth.py", "text": "import os"},
        {"path": "src/auth.py", "text": "def login(): pass"},
        {"path": "src/other.py", "text": "def foo(): pass"},
    ]
    score_suboptimal = compute_ndcg_at_k(items_suboptimal, expected_files, expected_symbols, k=3)
    assert 0.70 < score_suboptimal < 0.90


def test_symbol_recall_at_k():
    chunks = [
        {"path": "src/a.py", "text": "function create_token() {}"},
        {"path": "src/b.py", "text": "function verify_token() {}"},
    ]
    assert compute_symbol_recall_at_k(chunks, ["create_token"], k=1) == 1.0
    assert compute_symbol_recall_at_k(chunks, ["create_token", "verify_token"], k=1) == 0.5
    assert compute_symbol_recall_at_k(chunks, ["create_token", "verify_token"], k=2) == 1.0
    assert compute_symbol_recall_at_k(chunks, ["missing_symbol"], k=2) == 0.0


def test_must_mention_and_citation_metrics():
    text = "The user authentication is implemented with JWT access tokens and password hashing."
    must_mention = ["jwt", "authentication", "tokens"]
    assert compute_must_mention_coverage(text, must_mention) == 1.0

    must_mention_partial = ["jwt", "oauth2"]
    assert compute_must_mention_coverage(text, must_mention_partial) == 0.5

    citations = ["S1", "S2"]
    cited_files = ["backend/app/auth.py", "backend/app/db.py"]
    expected_files = ["backend/app/auth.py"]
    valid_source_ids = {"S1", "S2", "S3"}

    res = compute_citation_metrics(citations, cited_files, expected_files, valid_source_ids)
    assert res["validity"] == 1.0
    assert res["precision"] == 0.5
    assert res["recall"] == 1.0


def test_brier_score_and_ece():
    # 3 predictions: confidence 0.9 (correct=1), 0.8 (correct=1), 0.2 (correct=0)
    confidences = [0.9, 0.8, 0.2]
    correctness = [1.0, 1.0, 0.0]

    # Brier: ((0.9-1)^2 + (0.8-1)^2 + (0.2-0)^2) / 3 = (0.01 + 0.04 + 0.04) / 3 = 0.03
    brier = compute_brier_score(confidences, correctness)
    assert brier == 0.03

    ece, bins = compute_ece_and_bins(confidences, correctness, num_bins=10)
    assert isinstance(ece, float)
    assert len(bins) == 10
    # Check that bins have counts and accuracy
    non_empty_bins = [b for b in bins if b["count"] > 0]
    assert len(non_empty_bins) >= 2


def test_percentiles():
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p50, p95 = compute_percentiles(values)
    assert p50 == 50.0
    assert p95 == 90.0
