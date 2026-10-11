from app.services.chat.cache import build_answer_cache_key
from app.services.chat.citations import verify_and_clean_citations
from app.services.chat.confidence import compute_confidence


def test_verify_and_clean_citations_success() -> None:
    sources_map = {
        "S1": {
            "path": "app/auth.py",
            "start_line": 10,
            "end_line": 20,
            "symbol_name": "AuthService.login",
        },
        "S2": {
            "path": "app/db.py",
            "start_line": 1,
            "end_line": 50,
            "symbol_name": "get_db",
        },
    }

    text = "The user logs in via `login` [S1]. The database session is handled by `get_db` [S2]. An invalid claim was made [S99]."

    res = verify_and_clean_citations(text, sources_map)

    assert len(res.valid) == 2
    assert res.valid[0].source_id == "S1"
    assert res.valid[0].path == "app/auth.py"
    assert res.valid[0].symbol == "AuthService.login"
    assert res.valid[1].source_id == "S2"

    assert "S99" in res.removed
    assert "[S99]" not in res.cleaned_text
    assert "[S1]" in res.cleaned_text
    assert "[S2]" in res.cleaned_text


def test_confidence_calculation_full() -> None:
    sources_map = {
        "S1": {"rerank_score": 2.5, "path": "app/main.py"},
        "S2": {"rerank_score": 1.8, "path": "app/db.py"},
    }

    text = """Login is performed by the service [S1].

The database is queried [S2]."""

    res = verify_and_clean_citations(text, sources_map)

    conf = compute_confidence(
        text=res.cleaned_text,
        sources_map=sources_map,
        valid_citations=res.valid,
        total_citations_found=res.total_found,
        intent="locate",
        grounding_verdict="supported",
        insufficient=False,
    )

    assert conf.score >= 0.75
    assert conf.label == "High"
    assert conf.factors.r > 0.8
    assert conf.factors.c == 1.0
    assert conf.factors.k == 1.0
    assert conf.factors.g == 1.0


def test_confidence_insufficient_capping() -> None:
    sources_map = {
        "S1": {"rerank_score": 0.1, "path": "app/main.py"},
    }

    text = "Something was found [S1]."
    res = verify_and_clean_citations(text, sources_map)

    conf = compute_confidence(
        text=res.cleaned_text,
        sources_map=sources_map,
        valid_citations=res.valid,
        total_citations_found=res.total_found,
        intent="locate",
        grounding_verdict="partial",
        insufficient=True,
    )

    assert conf.score <= 0.35
    assert conf.insufficient is True


def test_confidence_general_intent() -> None:
    conf = compute_confidence(
        text="A closure is a function object...",
        sources_map={},
        valid_citations=[],
        total_citations_found=0,
        intent="general",
    )
    assert conf.score == 0.0
    assert conf.label == "N/A"


def test_answer_cache_key_generation() -> None:
    key1 = build_answer_cache_key(
        repo_id="repo123",
        commit_sha="abc1234",
        embedding_model="jina",
        strategy="hybrid",
        prompt_version="1.0.0",
        question="Where is JWT created?",
    )
    key2 = build_answer_cache_key(
        repo_id="repo123",
        commit_sha="abc1234",
        embedding_model="jina",
        strategy="hybrid",
        prompt_version="1.0.0",
        question="where is jwt created",
    )
    assert key1.startswith("cache:answer:")
    # Normalised questions should produce identical cache keys
    assert key1 == key2
