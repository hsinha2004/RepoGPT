"""
Base interface and utilities for AST code extractors (§8.4).
"""

from abc import ABC, abstractmethod

from app.services.parsing.models import ParsedFile, SymbolInfo


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, source: str, path: str = "") -> ParsedFile:
        """Extracts symbols, imports, docstring, and entry points from source code."""
        pass

    def build_file_card(
        self,
        path: str,
        language: str,
        module_docstring: str | None,
        imports: list[str],
        symbols: list[SymbolInfo],
    ) -> str:
        """Constructs a deterministic file card summary for the file (§8.5)."""
        lines: list[str] = [
            f"# File: {path}",
            f"Language: {language}",
        ]
        if module_docstring:
            first_doc_line = module_docstring.strip().split("\n")[0].strip()
            lines.append(f"Summary: {first_doc_line}")

        if imports:
            clean_imports = sorted(set(imports))[:15]
            lines.append(f"Imports: {', '.join(clean_imports)}")

        top_level_symbols = [s for s in symbols if s.parent is None]
        if top_level_symbols:
            lines.append("Symbols:")
            for s in top_level_symbols[:25]:
                sym_line = f"  - {s.kind} {s.name}: {s.signature}"
                if s.docstring:
                    doc_summary = s.docstring.strip().split("\n")[0].strip()
                    sym_line += f" -- {doc_summary}"
                lines.append(sym_line)

        return "\n".join(lines)
