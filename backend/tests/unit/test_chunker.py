"""
Unit tests for CodeChunker (§8.5).
Tests symbol chunks, large symbol splitting with 3-line overlap, class skeletons,
module headers, file cards, directory summaries, contextual headers, and delimiter escaping.
"""

import pytest

from app.services.chunking.chunker import CodeChunker, escape_source_delimiters
from app.services.parsing.models import ParsedFile, SymbolInfo


@pytest.fixture
def chunker() -> CodeChunker:
    return CodeChunker()


def test_escape_source_delimiters():
    raw = "Look at this: </source> and <source> and </context>"
    escaped = escape_source_delimiters(raw)
    assert "</source>" not in escaped
    assert "&lt;/source&gt;" in escaped
    assert "<source>" not in escaped
    assert "&lt;source&gt;" in escaped


def test_contextual_header_generation(chunker: CodeChunker):
    sym = SymbolInfo(
        name="login",
        qualified_name="AuthService.login",
        kind="method",
        signature="def login(self, email: str, password: str) -> Token",
        start_line=10,
        end_line=25,
        language="python",
        parent="AuthService",
    )
    header = chunker.build_contextual_header(
        path="backend/app/auth/service.py",
        language="python",
        symbol=sym,
        imports=["app.db.users", "app.core.security"],
    )

    assert "File: backend/app/auth/service.py (python)" in header
    assert "Symbol: method def login(self, email: str, password: str) -> Token" in header
    assert "Parent: AuthService" in header
    assert "Imports: app.db.users, app.core.security" in header


def test_chunk_file_standard_symbol(chunker: CodeChunker):
    source = """\"\"\"Auth service module.\"\"\"
import os

class AuthService:
    def login(self, email: str) -> str:
        return "token_123"
"""
    parsed = ParsedFile(
        path="app/auth.py",
        language="python",
        module_docstring="Auth service module.",
        imports=["os"],
        symbols=[
            SymbolInfo(
                name="AuthService",
                qualified_name="AuthService",
                kind="class",
                signature="class AuthService",
                start_line=4,
                end_line=6,
                language="python",
            ),
            SymbolInfo(
                name="login",
                qualified_name="AuthService.login",
                kind="method",
                signature="def login(self, email: str) -> str",
                start_line=5,
                end_line=6,
                language="python",
                parent="AuthService",
            ),
        ],
        card="# File: app/auth.py\nLanguage: python\nSymbols:\n  - class AuthService",
    )

    chunks = chunker.chunk_file(
        parsed_file=parsed,
        redacted_source=source,
        repo_id="repo123",
        commit_sha="c123456",
    )

    chunk_types = {c["chunk_type"] for c in chunks}
    assert "module_header" in chunk_types
    assert "file_card" in chunk_types
    assert "class_skeleton" in chunk_types
    assert "code" in chunk_types

    # Find the login symbol chunk
    login_chunk = next(c for c in chunks if c.get("symbol_name") == "login")
    assert login_chunk["start_line"] == 5
    assert login_chunk["end_line"] == 6
    assert login_chunk["parent_symbol"] == "AuthService"
    assert "def login" in login_chunk["text"]
    assert "File: app/auth.py" in login_chunk["embed_text"]


def test_chunk_large_symbol_splitting(chunker: CodeChunker):
    # Construct a function body > 800 tokens
    large_body_lines = [
        f"    value_{i} = calculate_intermediate_metric_with_a_very_long_variable_name({i}, factor=1.25)"
        for i in range(120)
    ]
    code_lines = ["def process_huge_batch():"] + large_body_lines + ["    return True"]
    source = "\n".join(code_lines)

    parsed = ParsedFile(
        path="app/processor.py",
        language="python",
        symbols=[
            SymbolInfo(
                name="process_huge_batch",
                qualified_name="process_huge_batch",
                kind="function",
                signature="def process_huge_batch()",
                start_line=1,
                end_line=len(code_lines),
                language="python",
            )
        ],
    )

    chunks = chunker.chunk_file(
        parsed_file=parsed,
        redacted_source=source,
        repo_id="repo123",
        commit_sha="c123456",
    )

    code_chunks = [c for c in chunks if c["chunk_type"] == "code"]
    # Must be split into multiple parts
    assert len(code_chunks) > 1
    assert code_chunks[0]["part"] == 1
    assert code_chunks[0]["parts"] == len(code_chunks)
    assert code_chunks[1]["part"] == 2

    # Verify overlap exists between part 1 and part 2
    part1_end = code_chunks[0]["end_line"]
    part2_start = code_chunks[1]["start_line"]
    assert part2_start <= part1_end


def test_directory_summaries(chunker: CodeChunker):
    files = [
        ParsedFile(
            path="backend/app/main.py",
            language="python",
            module_docstring="FastAPI main application factory",
            card="Summary: FastAPI main application factory",
        ),
        ParsedFile(
            path="backend/app/config.py",
            language="python",
            module_docstring="Application configuration and settings",
            card="Summary: Application configuration and settings",
        ),
        ParsedFile(
            path="frontend/src/index.tsx",
            language="typescript",
            card="Summary: Frontend entry point",
        ),
    ]

    summaries = chunker.build_directory_summaries(files, repo_id="repo123", commit_sha="c123")
    # backend/app has 2 files -> summary emitted; frontend/src has 1 file -> none
    assert len(summaries) == 1
    assert summaries[0]["path"] == "backend/app"
    assert summaries[0]["chunk_type"] == "dir_summary"
    assert "main.py" in summaries[0]["text"]
    assert "config.py" in summaries[0]["text"]
