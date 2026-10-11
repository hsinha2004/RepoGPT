"""
Documentation extractor for Markdown, RST, and plain text (§8.4).
Extracts hierarchical heading tree and doc metadata.
"""

import re

from app.services.parsing.extractors.base import BaseExtractor
from app.services.parsing.models import ParsedFile, SymbolInfo


class DocsExtractor(BaseExtractor):
    def extract(self, source: str, path: str = "") -> ParsedFile:
        lines = source.splitlines()
        symbols: list[SymbolInfo] = []
        heading_re = re.compile(r"^(#{1,6})\s+(.*)$")

        current_heading: tuple[int, str, int] | None = None  # (level, title, start_line)

        for idx, line in enumerate(lines, 1):
            m = heading_re.match(line.strip())
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()

                if current_heading:
                    c_level, c_title, c_start = current_heading
                    symbols.append(
                        SymbolInfo(
                            name=c_title,
                            qualified_name=f"{path} > {c_title}",
                            kind="section",
                            signature=f"{'#' * c_level} {c_title}",
                            start_line=c_start,
                            end_line=idx - 1,
                            language="markdown",
                            exported=True,
                        )
                    )
                current_heading = (level, title, idx)

        if current_heading:
            c_level, c_title, c_start = current_heading
            symbols.append(
                SymbolInfo(
                    name=c_title,
                    qualified_name=f"{path} > {c_title}",
                    kind="section",
                    signature=f"{'#' * c_level} {c_title}",
                    start_line=c_start,
                    end_line=len(lines) if lines else 1,
                    language="markdown",
                    exported=True,
                )
            )

        doc_summary = symbols[0].name if symbols else "Documentation file"
        card = self.build_file_card(
            path=path,
            language="markdown",
            module_docstring=doc_summary,
            imports=[],
            symbols=symbols,
        )

        return ParsedFile(
            path=path,
            language="markdown",
            symbols=symbols,
            imports=[],
            module_docstring=doc_summary,
            top_level_ranges=[(1, len(lines))] if lines else [],
            card=card,
        )
