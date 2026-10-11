"""
Fallback Extractor for unsupported languages or parse failures (§8.4).
Produces 60-line windows with 10-line overlap.
"""

from app.services.parsing.extractors.base import BaseExtractor
from app.services.parsing.models import ParsedFile, SymbolInfo


class FallbackExtractor(BaseExtractor):
    def extract(self, source: str, path: str = "") -> ParsedFile:
        lines = source.splitlines()
        total_lines = len(lines)
        symbols: list[SymbolInfo] = []

        window_size = 60
        overlap = 10
        step = max(1, window_size - overlap)

        start = 1
        window_idx = 1
        while start <= total_lines:
            end = min(total_lines, start + window_size - 1)
            first_line = lines[start - 1].strip() if lines and start <= total_lines else ""
            symbols.append(
                SymbolInfo(
                    name=f"lines_{start}_{end}",
                    qualified_name=f"{path}#L{start}-L{end}",
                    kind="const",
                    signature=f"Window {window_idx}: lines {start}-{end} ({first_line[:40]})",
                    start_line=start,
                    end_line=end,
                    language="generic",
                    exported=True,
                )
            )
            window_idx += 1
            if end >= total_lines:
                break
            start += step

        card = self.build_file_card(
            path=path,
            language="generic",
            module_docstring="Source file (generic)",
            imports=[],
            symbols=symbols,
        )

        return ParsedFile(
            path=path,
            language="generic",
            symbols=symbols,
            imports=[],
            module_docstring="Generic source file",
            top_level_ranges=[(1, total_lines)] if total_lines else [],
            card=card,
            warnings=[f"Used fallback line-window parser for {path}"],
        )
