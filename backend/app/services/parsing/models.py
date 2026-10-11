"""
Data structures for AST extraction results (§8.4).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SymbolInfo:
    name: str
    qualified_name: str
    kind: str  # function, method, class, interface, struct, enum, type, const, component
    signature: str
    start_line: int  # 1-based inclusive
    end_line: int  # 1-based inclusive
    language: str
    docstring: str | None = None
    parent: str | None = None
    exported: bool = True
    chunk_ids: list[str] = field(default_factory=list)

    def to_dict(self, repo_id: str = "", path: str = "") -> dict[str, Any]:
        return {
            "repo_id": repo_id,
            "path": path,
            "name": self.name,
            "name_lower": self.name.lower(),
            "qualified_name": self.qualified_name,
            "kind": self.kind,
            "signature": self.signature,
            "docstring": self.docstring,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "parent": self.parent,
            "language": self.language,
            "exported": self.exported,
            "chunk_ids": self.chunk_ids,
        }


@dataclass
class EntryPointHint:
    reason: str
    line: int
    symbol: str | None = None


@dataclass
class ParsedFile:
    path: str
    language: str
    symbols: list[SymbolInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    module_docstring: str | None = None
    top_level_ranges: list[tuple[int, int]] = field(default_factory=list)
    entry_point_hints: list[EntryPointHint] = field(default_factory=list)
    card: str = ""
    warnings: list[str] = field(default_factory=list)
