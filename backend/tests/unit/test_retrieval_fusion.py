from app.services.retrieval.fusion import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_math() -> None:
    # RRF_K = 60
    # chunk_A is rank 1 in BM25 (weight 0.5) and rank 2 in Vector (weight 0.5)
    # score(chunk_A) = 0.5 / (60 + 1) + 0.5 / (60 + 2) = 0.5/61 + 0.5/62 = 0.0081967 + 0.0080645 = 0.0162612
    # chunk_B is rank 1 in Vector (weight 0.5), not in BM25
    # score(chunk_B) = 0.5 / (60 + 1) = 0.0081967
    bm25 = [("chunk_A", 1, 10.5)]
    vector = [("chunk_B", 1, 0.95), ("chunk_A", 2, 0.85)]

    fused = reciprocal_rank_fusion(
        bm25_results=bm25,
        vector_results=vector,
        rrf_k=60,
        bm25_weight=0.5,
        vector_weight=0.5,
    )

    assert len(fused) == 2
    assert fused[0].chunk_id == "chunk_A"
    assert fused[1].chunk_id == "chunk_B"
    assert fused[0].rrf_score > fused[1].rrf_score
    assert fused[0].ranks.bm25 == 1
    assert fused[0].ranks.vector == 2
    assert fused[1].ranks.vector == 1
    assert fused[1].ranks.bm25 is None


def test_symbol_boost_in_fusion() -> None:
    # Symbol lookup has default weight 1.0
    # chunk_sym has rank 1 in symbol
    # score = 1.0 / (60 + 1) = 0.016393
    # chunk_bm25 has rank 1 in bm25 with weight 0.5 -> 0.008196
    bm25 = [("chunk_bm25", 1, 15.0)]
    symbol = [("chunk_sym", 1, {"name": "AuthService"})]

    fused = reciprocal_rank_fusion(
        bm25_results=bm25,
        symbol_results=symbol,
        rrf_k=60,
        bm25_weight=0.5,
        symbol_weight=1.0,
    )

    assert fused[0].chunk_id == "chunk_sym"
    assert fused[0].ranks.symbol == 1
    assert fused[1].chunk_id == "chunk_bm25"


def test_empty_candidate_lists() -> None:
    fused = reciprocal_rank_fusion()
    assert fused == []
