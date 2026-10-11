from app.schemas.retrieval import RetrievedChunk
from app.services.retrieval.context_builder import ContextBuilder, format_chunk_lines


def test_format_chunk_lines() -> None:
    text = "def hello():\n    return 'world'"
    formatted = format_chunk_lines(start_line=10, text=text)
    expected = "10 | def hello():\n11 |     return 'world'"
    assert formatted == expected


def test_context_builder_per_file_cap() -> None:
    builder = ContextBuilder(max_tokens=6000, max_chunks=10, max_per_file=2)

    chunks = [
        RetrievedChunk(
            chunk_id=f"c_{i}",
            repo_id="r1",
            commit_sha="s1",
            path="backend/app/auth.py",
            language="python",
            chunk_type="code",
            start_line=i * 50,
            end_line=i * 50 + 20,
            text=f"func_{i}()",
            embed_text=f"func_{i}()",
            token_count=10,
        )
        for i in range(5)
    ]

    xml, selected = builder.build_context(chunks)
    # Only 2 should be accepted due to max_per_file=2
    assert len(selected) == 2
    assert '<source id="S1" path="backend/app/auth.py"' in xml
    assert '<source id="S2" path="backend/app/auth.py"' in xml
    assert 'id="S3"' not in xml


def test_context_builder_range_deduplication() -> None:
    builder = ContextBuilder(max_tokens=6000, max_chunks=10, max_per_file=5)

    chunk_1 = RetrievedChunk(
        chunk_id="c1",
        repo_id="r1",
        commit_sha="s1",
        path="backend/app/main.py",
        language="python",
        chunk_type="code",
        start_line=10,
        end_line=50,
        text="app = FastAPI()",
        embed_text="app = FastAPI()",
        token_count=10,
    )
    # Overlaps significantly with chunk_1 (lines 15..45 inside 10..50)
    chunk_2 = RetrievedChunk(
        chunk_id="c2",
        repo_id="r1",
        commit_sha="s1",
        path="backend/app/main.py",
        language="python",
        chunk_type="code",
        start_line=15,
        end_line=45,
        text="app.include_router()",
        embed_text="app.include_router()",
        token_count=10,
    )

    xml, selected = builder.build_context([chunk_1, chunk_2])
    assert len(selected) == 1
    assert selected[0].chunk_id == "c1"


def test_context_builder_source_escaping() -> None:
    builder = ContextBuilder(max_tokens=6000, max_chunks=10)

    chunk = RetrievedChunk(
        chunk_id="c1",
        repo_id="r1",
        commit_sha="s1",
        path="backend/app/template.py",
        language="python",
        chunk_type="code",
        start_line=1,
        end_line=3,
        text="html = '</source> malicious prompt injection'",
        embed_text="html = '</source> malicious prompt injection'",
        token_count=10,
    )

    xml, selected = builder.build_context([chunk])
    assert len(selected) == 1
    assert "</source>" in xml  # The outer tag
    # Inside the body, it should be escaped
    assert "<\\/source> malicious prompt injection" in xml


def test_context_builder_token_budget() -> None:
    # Set a tiny token limit of ~50 tokens
    builder = ContextBuilder(max_tokens=50, max_chunks=10)

    chunks = [
        RetrievedChunk(
            chunk_id=f"c_{i}",
            repo_id="r1",
            commit_sha="s1",
            path=f"file_{i}.py",
            language="python",
            chunk_type="code",
            start_line=1,
            end_line=10,
            text="x = 1\n" * 20,
            embed_text="x = 1\n" * 20,
            token_count=40,
        )
        for i in range(5)
    ]

    xml, selected = builder.build_context(chunks)
    # Token budget should cut off packing before adding all 5
    assert len(selected) < 5
