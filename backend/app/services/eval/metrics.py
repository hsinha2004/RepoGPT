from __future__ import annotations

import math
from typing import Any


def compute_hit_at_k(retrieved_files: list[str], expected_files: list[str], k: int) -> float:
    """Computes Hit@k: 1.0 if any retrieved file in top k is in expected_files, else 0.0."""
    if not expected_files or not retrieved_files:
        return 0.0
    top_k = set(retrieved_files[:k])
    expected_set = set(expected_files)
    return 1.0 if (top_k & expected_set) else 0.0


def compute_precision_at_k(retrieved_files: list[str], expected_files: list[str], k: int) -> float:
    """Computes Precision@k on unique files retrieved."""
    if not retrieved_files or not expected_files or k <= 0:
        return 0.0
    # Keep order but deduplicate files
    seen: set[str] = set()
    unique_top_k: list[str] = []
    for f in retrieved_files:
        if f not in seen:
            seen.add(f)
            unique_top_k.append(f)
        if len(unique_top_k) >= k:
            break

    if not unique_top_k:
        return 0.0

    expected_set = set(expected_files)
    hits = sum(1 for f in unique_top_k if f in expected_set)
    return hits / len(unique_top_k)


def compute_recall_at_k(retrieved_files: list[str], expected_files: list[str], k: int) -> float:
    """Computes Recall@k on unique files retrieved."""
    if not expected_files:
        return 1.0
    if not retrieved_files or k <= 0:
        return 0.0

    seen: set[str] = set()
    unique_top_k: list[str] = []
    for f in retrieved_files:
        if f not in seen:
            seen.add(f)
            unique_top_k.append(f)
        if len(unique_top_k) >= k:
            break

    expected_set = set(expected_files)
    hits = sum(1 for f in unique_top_k if f in expected_set)
    return hits / len(expected_set)


def compute_mrr(retrieved_files: list[str], expected_files: list[str]) -> float:
    """Computes Mean Reciprocal Rank (MRR): 1 / rank of first relevant file."""
    if not expected_files or not retrieved_files:
        return 0.0
    expected_set = set(expected_files)
    for rank, f in enumerate(retrieved_files, start=1):
        if f in expected_set:
            return 1.0 / rank
    return 0.0


def compute_ndcg_at_k(
    retrieved_items: list[dict[str, Any]],
    expected_files: list[str],
    expected_symbols: list[str],
    k: int,
) -> float:
    """Computes nDCG@k with graded relevance (2 for symbol+file, 1 for file, 0 otherwise)."""
    if not expected_files or not retrieved_items or k <= 0:
        return 0.0

    expected_files_set = set(expected_files)
    expected_symbols_set = {s.lower() for s in expected_symbols}

    # Compute actual relevance scores for top k items
    actual_rels: list[int] = []
    for item in retrieved_items[:k]:
        path = item.get("path", "")
        text = (item.get("text") or item.get("snippet") or "").lower()

        if path in expected_files_set:
            has_symbol = (
                any(sym in text for sym in expected_symbols_set) if expected_symbols_set else False
            )
            rel = 2 if has_symbol else 1
        else:
            rel = 0
        actual_rels.append(rel)

    # Compute DCG@k
    dcg = sum((2**rel - 1) / math.log2(idx + 1) for idx, rel in enumerate(actual_rels, start=1))

    # Compute Ideal DCG@k (IDCG)
    # The ideal relevance list would have all 2s first, then 1s, then 0s
    ideal_rels = sorted(actual_rels, reverse=True)
    # If there are fewer than k items or ideal is all 0, check against potential perfect score
    if sum(ideal_rels) == 0:
        return 0.0

    idcg = sum((2**rel - 1) / math.log2(idx + 1) for idx, rel in enumerate(ideal_rels, start=1))
    if idcg <= 0.0:
        return 0.0

    return min(1.0, dcg / idcg)


def compute_symbol_recall_at_k(
    retrieved_chunks: list[dict[str, Any]],
    expected_symbols: list[str],
    k: int,
) -> float:
    """Computes Symbol Recall@k: fraction of expected symbols found in top k chunks."""
    if not expected_symbols:
        return 1.0
    if not retrieved_chunks or k <= 0:
        return 0.0

    top_k_chunks = retrieved_chunks[:k]
    combined_text = " ".join(
        (c.get("text") or c.get("snippet") or "") for c in top_k_chunks
    ).lower()

    found_count = sum(1 for sym in expected_symbols if sym.lower() in combined_text)
    return found_count / len(expected_symbols)


def compute_must_mention_coverage(text: str, must_mention: list[str]) -> float:
    """Computes fraction of must_mention phrases present in text (case-insensitive)."""
    if not must_mention:
        return 1.0
    if not text:
        return 0.0

    lower_text = text.lower()
    hits = sum(1 for phrase in must_mention if phrase.lower() in lower_text)
    return hits / len(must_mention)


def compute_citation_metrics(
    citations: list[str],
    cited_files: list[str],
    expected_files: list[str],
    valid_source_ids: set[str],
) -> dict[str, float]:
    """Computes citation validity, precision, and recall (§14.2)."""
    if not citations:
        validity = 1.0 if not expected_files else 0.0
        return {
            "validity": validity,
            "precision": 0.0,
            "recall": 0.0,
        }

    valid_citations = sum(1 for c in citations if c in valid_source_ids)
    validity = valid_citations / len(citations) if citations else 1.0

    if not cited_files:
        return {
            "validity": validity,
            "precision": 0.0,
            "recall": 0.0,
        }

    expected_set = set(expected_files)
    unique_cited = set(cited_files)

    hits = sum(1 for f in unique_cited if f in expected_set)
    precision = hits / len(unique_cited) if unique_cited else 0.0
    recall = hits / len(expected_set) if expected_set else 1.0

    return {
        "validity": round(validity, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


def compute_brier_score(confidences: list[float], correctness: list[float]) -> float:
    """Computes Brier score: (1/N) * sum((confidence - correctness)^2)."""
    if not confidences or not correctness or len(confidences) != len(correctness):
        return 0.0
    n = len(confidences)
    sq_err = sum((conf - corr) ** 2 for conf, corr in zip(confidences, correctness, strict=False))
    return round(sq_err / n, 4)


def compute_ece_and_bins(
    confidences: list[float],
    correctness: list[float],
    num_bins: int = 10,
) -> tuple[float, list[dict[str, Any]]]:
    """Computes Expected Calibration Error (ECE) and reliability diagram bins."""
    if not confidences or not correctness or len(confidences) != len(correctness):
        bins = [
            {
                "bin_center": round((i + 0.5) / num_bins, 2),
                "confidence_avg": 0.0,
                "accuracy": 0.0,
                "count": 0,
            }
            for i in range(num_bins)
        ]
        return 0.0, bins

    n = len(confidences)
    bin_items: list[list[tuple[float, float]]] = [[] for _ in range(num_bins)]

    for conf, corr in zip(confidences, correctness, strict=False):
        b_idx = min(int(conf * num_bins), num_bins - 1)
        bin_items[b_idx].append((conf, corr))

    ece = 0.0
    bins_out: list[dict[str, Any]] = []

    for i in range(num_bins):
        items = bin_items[i]
        bin_center = round((i + 0.5) / num_bins, 2)
        count = len(items)
        if count > 0:
            avg_conf = sum(c[0] for c in items) / count
            acc = sum(c[1] for c in items) / count
            ece += (count / n) * abs(acc - avg_conf)
            bins_out.append(
                {
                    "bin_center": bin_center,
                    "confidence_avg": round(avg_conf, 4),
                    "accuracy": round(acc, 4),
                    "count": count,
                }
            )
        else:
            bins_out.append(
                {
                    "bin_center": bin_center,
                    "confidence_avg": round(bin_center, 4),
                    "accuracy": 0.0,
                    "count": 0,
                }
            )

    return round(ece, 4), bins_out


def compute_percentiles(values: list[float]) -> tuple[float, float]:
    """Computes (p50, p95) percentiles from a list of numerical values."""
    if not values:
        return 0.0, 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    p50_idx = int(0.50 * (n - 1))
    p95_idx = int(0.95 * (n - 1))
    return round(sorted_v[p50_idx], 2), round(sorted_v[p95_idx], 2)
