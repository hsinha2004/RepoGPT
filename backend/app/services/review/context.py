"""
Context retrieval and symbol mapping engine for code review (§10.2).
"""

from __future__ import annotations

from typing import Any

import structlog

from app.db.repositories.files import FileRepository
from app.db.repositories.symbols import SymbolRepository
from app.services.parsing.registry import ParserRegistry
from app.services.review.diff_parser import ParsedFileDiff

logger = structlog.get_logger(__name__)


class ReviewContextBuilder:
    """
    Maps diff hunks to enclosing symbols and retrieves multi-faceted repository context (§10.2).
    """

    def __init__(
        self,
        symbol_repo: SymbolRepository,
        file_repo: FileRepository,
        parser_registry: ParserRegistry | None = None,
    ) -> None:
        self.symbol_repo = symbol_repo
        self.file_repo = file_repo
        self.parser_registry = parser_registry or ParserRegistry()

    async def map_symbols(
        self,
        repo_id: str,
        path: str,
        head_content: str,
        file_diff: ParsedFileDiff,
    ) -> list[dict[str, Any]]:
        """
        Parses head content with tree-sitter to find symbols enclosing changed lines,
        and compares with base symbols to classify as added / modified / removed.
        """
        changed_lines = set(file_diff.changed_new_lines)
        if not changed_lines and not file_diff.is_added and not file_diff.is_deleted:
            return []

        # Parse head symbols
        head_symbols: list[dict[str, Any]] = []
        if head_content:
            try:
                parsed_file = self.parser_registry.parse_file(head_content, path)
                for s in parsed_file.symbols:
                    head_symbols.append({
                        "name": s.name,
                        "kind": s.kind,
                        "start_line": s.start_line,
                        "end_line": s.end_line,
                        "signature": getattr(s, "signature", None),
                    })
            except Exception as exc:
                logger.warning("head_symbol_extraction_failed", path=path, error=str(exc))

        # Query base symbols from database
        base_symbols = await self.symbol_repo.list_for_file(repo_id, path)
        base_by_name = {s.get("name"): s for s in base_symbols if s.get("name")}

        mapped: list[dict[str, Any]] = []

        if file_diff.is_added:
            for hs in head_symbols:
                mapped.append({
                    "name": hs["name"],
                    "kind": hs["kind"],
                    "start_line": hs["start_line"],
                    "end_line": hs["end_line"],
                    "status": "added",
                })
            return mapped

        if file_diff.is_deleted:
            for bs in base_symbols:
                mapped.append({
                    "name": bs.get("name", "unknown"),
                    "kind": bs.get("kind", "symbol"),
                    "start_line": bs.get("start_line", 1),
                    "end_line": bs.get("end_line", 1),
                    "status": "removed",
                })
            return mapped

        # Modified file: find which head symbols encompass any changed lines
        for hs in head_symbols:
            s_start = hs["start_line"]
            s_end = hs["end_line"]
            # Check overlap with changed lines
            if any(s_start <= ln <= s_end for ln in changed_lines):
                base_s = base_by_name.get(hs["name"])
                status = "modified" if base_s else "added"
                mapped.append({
                    "name": hs["name"],
                    "kind": hs["kind"],
                    "start_line": s_start,
                    "end_line": s_end,
                    "status": status,
                })

        return mapped

    async def retrieve_file_context(
        self,
        repo_id: str,
        path: str,
        changed_symbols: list[dict[str, Any]],
        token_budget: int = 4000,
    ) -> list[dict[str, Any]]:
        """
        Retrieves context items (callers, related tests, conventions) capped by token budget.
        Assigns sequential IDs C1, C2, ...
        """
        if token_budget <= 0:
            return []

        context_items: list[dict[str, Any]] = []
        c_counter = 1

        # 1. Related Test Files (e.g., test_<name>.py or tests/<name>_test.go)
        base_name = path.split("/")[-1].split(".")[0]
        test_candidates = [
            f"tests/test_{base_name}.py",
            f"tests/{base_name}_test.py",
            f"backend/tests/test_{base_name}.py",
            f"{path.replace('.py', '_test.py')}",
        ]
        if changed_symbols:
            for s in changed_symbols:
                s_name = s.get("name")
                if s_name:
                    test_candidates.append(f"tests/test_{s_name}.py")
        for t_path in test_candidates:
            file_doc = await self.file_repo.get_by_path(repo_id, t_path)
            if file_doc:
                snippet = file_doc.get("content", "")[:600]
                context_items.append({
                    "source_id": f"C{c_counter}",
                    "path": t_path,
                    "start_line": 1,
                    "end_line": min(30, file_doc.get("line_count", 30)),
                    "category": "test",
                    "snippet": snippet,
                })
                c_counter += 1
                break

        # 2. Conventions (CONTRIBUTING, linter config)
        convention_paths = ["CONTRIBUTING.md", ".editorconfig", "pyproject.toml"]
        for c_path in convention_paths:
            c_doc = await self.file_repo.get_by_path(repo_id, c_path)
            if c_doc:
                snippet = c_doc.get("content", "")[:400]
                context_items.append({
                    "source_id": f"C{c_counter}",
                    "path": c_path,
                    "start_line": 1,
                    "end_line": 20,
                    "category": "convention",
                    "snippet": snippet,
                })
                c_counter += 1
                break

        return context_items
