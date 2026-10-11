from __future__ import annotations

import re
from typing import Any

from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.symbols import SymbolRepository

# Regex patterns for code identifier extraction
BACKTICK_RE = re.compile(r"`([^`]+)`")
DOTTED_ID_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
CAMEL_PASCAL_RE = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b")
SNAKE_CASE_RE = re.compile(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b")
FILE_PATH_RE = re.compile(
    r"\b[\w\-./]+\.(?:py|tsx?|jsx?|java|go|json|ya?ml|md|sql|toml|sh)\b",
    re.IGNORECASE,
)
CAPITALIZED_WORD_RE = re.compile(r"\b[A-Z][a-zA-Z0-9_]{2,}\b")


def extract_query_identifiers(query: str) -> list[str]:
    """Extracts likely code identifiers, dotted names, symbols, and file paths from a user query."""
    seen: set[str] = set()
    identifiers: list[str] = []

    def add(item: str) -> None:
        clean = item.strip().strip("'\"`(),:;{}[]")
        if clean and len(clean) >= 2 and clean not in seen:
            seen.add(clean)
            identifiers.append(clean)

    # 1. Backticked expressions
    for m in BACKTICK_RE.finditer(query):
        add(m.group(1))

    # 2. Dotted identifiers (e.g. AuthService.login, app.models.User)
    for m in DOTTED_ID_RE.finditer(query):
        add(m.group(0))

    # 3. File paths / basenames
    for m in FILE_PATH_RE.finditer(query):
        add(m.group(0))

    # 4. CamelCase / PascalCase
    for m in CAMEL_PASCAL_RE.finditer(query):
        add(m.group(0))

    # 5. snake_case
    for m in SNAKE_CASE_RE.finditer(query):
        add(m.group(0))

    # 6. Standalone capitalized class/symbol names
    for m in CAPITALIZED_WORD_RE.finditer(query):
        add(m.group(0))

    return identifiers


class SymbolLookupService:
    def __init__(
        self,
        symbol_repo: SymbolRepository,
        chunk_repo: ChunkRepository,
    ) -> None:
        self.symbol_repo = symbol_repo
        self.chunk_repo = chunk_repo

    async def lookup(
        self,
        repo_id: str,
        query: str,
        identifiers: list[str] | None = None,
        max_results: int = 20,
    ) -> list[tuple[str, int, dict[str, Any]]]:
        """Looks up chunks associated with symbols or file paths matching query identifiers.

        Returns a list of (chunk_id, rank, symbol_doc) tuples, ordered by rank ascending.
        Rank 1: exact qualified_name match
        Rank 2: exact name_lower match
        Rank 3: prefix match or file-path match
        """
        target_ids = identifiers if identifiers is not None else extract_query_identifiers(query)
        if not target_ids:
            return []

        matched_chunk_ranks: dict[str, tuple[int, dict[str, Any]]] = {}

        # 1. Exact qualified_name match (highest priority -> Rank 1)
        qname_symbols = await self.symbol_repo.find_by_qualified_names(repo_id, target_ids)
        for sym in qname_symbols:
            for cid in sym.get("chunk_ids", []):
                if cid not in matched_chunk_ranks:
                    matched_chunk_ranks[cid] = (1, sym)

        # 2. Exact name_lower match (Rank 2)
        name_symbols = await self.symbol_repo.find_by_name_lowers(repo_id, target_ids)
        for sym in name_symbols:
            for cid in sym.get("chunk_ids", []):
                if cid not in matched_chunk_ranks or matched_chunk_ranks[cid][0] > 2:
                    matched_chunk_ranks[cid] = (2, sym)

        # 3. Prefix search for identifiers >= 3 chars
        for ident in target_ids:
            if len(ident) >= 3 and len(matched_chunk_ranks) < max_results:
                prefix_symbols = await self.symbol_repo.search_by_prefix(repo_id, ident, limit=10)
                for sym in prefix_symbols:
                    for cid in sym.get("chunk_ids", []):
                        if cid not in matched_chunk_ranks:
                            matched_chunk_ranks[cid] = (3, sym)

        # 4. File path / basename matches
        file_paths = [i for i in target_ids if "." in i or "/" in i or "\\" in i]
        for fp in file_paths:
            basename = fp.replace("\\", "/").split("/")[-1].lower()
            # Fetch file card or symbol chunks for this file
            file_chunks = await self.chunk_repo.list_for_repo(
                repo_id=repo_id,
                chunk_type="file_card",
                limit=50,
            )
            for fc in file_chunks:
                fc_path = fc.get("path", "").lower()
                if fc_path.endswith(basename):
                    cid = fc.get("_id") or fc.get("chunk_id")
                    if cid and cid not in matched_chunk_ranks:
                        matched_chunk_ranks[str(cid)] = (
                            3,
                            {"name": basename, "path": fc.get("path"), "kind": "file"},
                        )

        # Sort by rank ascending
        sorted_results = sorted(
            [(cid, rank, sym) for cid, (rank, sym) in matched_chunk_ranks.items()],
            key=lambda x: x[1],
        )
        return sorted_results[:max_results]
