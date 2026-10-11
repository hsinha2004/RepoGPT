from __future__ import annotations

import tiktoken

from app.schemas.retrieval import RetrievedChunk

_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    try:
        return len(_encoder.encode(text))
    except Exception:
        # Fallback estimation: ~4 chars per token
        return max(1, len(text) // 4)


def format_chunk_lines(start_line: int, text: str) -> str:
    """Formats chunk text with original line numbers: '12 | code'."""
    lines = text.split("\n")
    formatted_lines: list[str] = []
    for offset, line in enumerate(lines):
        line_num = start_line + offset
        formatted_lines.append(f"{line_num} | {line}")
    return "\n".join(formatted_lines)


class ContextBuilder:
    def __init__(
        self,
        max_tokens: int = 6000,
        max_chunks: int = 8,
        max_per_file: int = 3,
    ) -> None:
        self.max_tokens = max_tokens
        self.max_chunks = max_chunks
        self.max_per_file = max_per_file

    def build_context(
        self,
        candidates: list[RetrievedChunk],
    ) -> tuple[str, list[RetrievedChunk]]:
        """Deduplicates, caps per file, packs into token/chunk budget, and formats XML context.

        Returns (formatted_xml_string, selected_chunks).
        """
        if not candidates:
            return "<sources>\n</sources>", []

        selected: list[RetrievedChunk] = []
        file_counts: dict[str, int] = {}
        file_ranges: dict[str, list[tuple[int, int]]] = {}

        for chunk in candidates:
            if len(selected) >= self.max_chunks:
                break

            path = chunk.path
            cur_count = file_counts.get(path, 0)
            if cur_count >= self.max_per_file:
                continue

            # Check overlap with existing selected chunks from this file
            ranges = file_ranges.get(path, [])
            c_start = chunk.start_line
            c_end = chunk.end_line

            # If heavily overlapping (> 70% overlap with an existing range), skip
            overlaps = False
            for r_start, r_end in ranges:
                overlap_start = max(c_start, r_start)
                overlap_end = min(c_end, r_end)
                if overlap_end >= overlap_start:
                    overlap_len = overlap_end - overlap_start + 1
                    chunk_len = max(1, c_end - c_start + 1)
                    if overlap_len / chunk_len >= 0.7:
                        overlaps = True
                        break

            if overlaps:
                continue

            # Accept chunk
            selected.append(chunk)
            file_counts[path] = cur_count + 1
            if path not in file_ranges:
                file_ranges[path] = []
            file_ranges[path].append((c_start, c_end))

        # Format sources with S1..Sn IDs
        source_blocks: list[str] = []
        final_selected: list[RetrievedChunk] = []
        total_tokens = count_tokens("<sources>\n</sources>\n")

        for idx, chunk in enumerate(selected, start=1):
            source_id = f"S{idx}"
            lines_attr = f"{chunk.start_line}-{chunk.end_line}"
            symbol_attr = f' symbol="{chunk.symbol_name}"' if chunk.symbol_name else ""
            lang_attr = f' language="{chunk.language}"' if chunk.language else ""

            body = format_chunk_lines(chunk.start_line, chunk.text)
            # Escape </source> in repository content
            safe_body = body.replace("</source>", "<\\/source>")

            block = (
                f'<source id="{source_id}" path="{chunk.path}" lines="{lines_attr}"'
                f"{symbol_attr}{lang_attr}>\n"
                f"{safe_body}\n"
                f"</source>"
            )

            block_tokens = count_tokens(block)
            if total_tokens + block_tokens > self.max_tokens and final_selected:
                # Token budget reached
                break

            total_tokens += block_tokens
            source_blocks.append(block)
            final_selected.append(chunk)

        if not source_blocks:
            xml_text = "<sources>\n</sources>"
        else:
            joined = "\n".join(source_blocks)
            xml_text = f"<sources>\n{joined}\n</sources>"

        return xml_text, final_selected
