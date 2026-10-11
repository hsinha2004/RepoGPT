"""
Code-Aware Chunker using tree-sitter AST and tiktoken cl100k_base (§8.5).
Generates symbol chunks, class skeletons, module headers, deterministic file cards,
directory summaries, doc/config chunks with contextual headers and delimiter escaping.
"""

import hashlib
from collections import defaultdict
from typing import Any

import tiktoken

from app.services.parsing.models import ParsedFile, SymbolInfo


def escape_source_delimiters(text: str) -> str:
    """Escapes XML/markdown-like source delimiters to prevent prompt injection."""
    return (
        text.replace("</source>", "&lt;/source&gt;")
        .replace("<source>", "&lt;source&gt;")
        .replace("</context>", "&lt;/context&gt;")
        .replace("<context>", "&lt;context&gt;")
    )


class CodeChunker:
    def __init__(self) -> None:
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self.encoder.encode(text, disallowed_special=()))

    def compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def build_contextual_header(
        self,
        path: str,
        language: str,
        symbol: SymbolInfo | None = None,
        imports: list[str] | None = None,
        heading_path: str | None = None,
    ) -> str:
        """
        Builds contextual header prepended to embed_text (§8.5):
        File: backend/app/auth/service.py (python)
        Symbol: method AuthService.login(...) -> Token
        Parent: class AuthService
        Imports: app.db.users, app.core.security
        """
        lines = [f"File: {path} ({language})"]
        if heading_path:
            lines.append(f"Section: {heading_path}")
        if symbol:
            sym_line = f"Symbol: {symbol.kind} {symbol.signature}"
            lines.append(sym_line)
            if symbol.parent:
                lines.append(f"Parent: {symbol.parent}")
        if imports:
            clean_imp = imports[:10]
            lines.append(f"Imports: {', '.join(clean_imp)}")
        return "\n".join(lines)

    def chunk_file(
        self,
        parsed_file: ParsedFile,
        redacted_source: str,
        repo_id: str,
        commit_sha: str,
    ) -> list[dict[str, Any]]:
        """
        Chunks a parsed file into symbol chunks, class skeletons,
        module header, and file card (§8.5).
        """
        chunks: list[dict[str, Any]] = []
        source_lines = redacted_source.splitlines()
        total_lines = len(source_lines)
        path = parsed_file.path
        lang = parsed_file.language

        # 1. Module Header Chunk (if file has docstring or imports)
        if parsed_file.module_docstring or parsed_file.imports:
            header_lines: list[str] = [f"# Module: {path} ({lang})"]
            if parsed_file.module_docstring:
                header_lines.append(f"Docstring:\n{parsed_file.module_docstring}")
            if parsed_file.imports:
                header_lines.append("Imports:\n" + "\n".join(parsed_file.imports))

            header_text = escape_source_delimiters("\n\n".join(header_lines))
            c_header = self.build_contextual_header(
                path=path, language=lang, imports=parsed_file.imports
            )
            embed_text = f"{c_header}\n\n{header_text}"
            token_count = self.count_tokens(embed_text)

            end_line = (
                max([r[1] for r in parsed_file.top_level_ranges], default=1)
                if parsed_file.top_level_ranges
                else min(30, total_lines)
            )

            chunks.append(
                {
                    "_id": f"{repo_id}:{path}:mod_header",
                    "repo_id": repo_id,
                    "commit_sha": commit_sha,
                    "path": path,
                    "language": lang,
                    "chunk_type": "module_header",
                    "symbol_name": None,
                    "symbol_kind": None,
                    "parent_symbol": None,
                    "start_line": 1,
                    "end_line": max(1, end_line),
                    "part": 1,
                    "parts": 1,
                    "text": header_text,
                    "embed_text": embed_text,
                    "token_count": token_count,
                    "content_hash": self.compute_hash(header_text),
                }
            )

        # 2. File Card Chunk (deterministic file summary)
        if parsed_file.card:
            card_text = escape_source_delimiters(parsed_file.card)
            c_header = self.build_contextual_header(
                path=path, language=lang, imports=parsed_file.imports
            )
            embed_text = f"{c_header}\n\n{card_text}"
            token_count = self.count_tokens(embed_text)
            chunks.append(
                {
                    "_id": f"{repo_id}:{path}:file_card",
                    "repo_id": repo_id,
                    "commit_sha": commit_sha,
                    "path": path,
                    "language": lang,
                    "chunk_type": "file_card",
                    "symbol_name": None,
                    "symbol_kind": None,
                    "parent_symbol": None,
                    "start_line": 1,
                    "end_line": max(1, total_lines),
                    "part": 1,
                    "parts": 1,
                    "text": card_text,
                    "embed_text": embed_text,
                    "token_count": token_count,
                    "content_hash": self.compute_hash(card_text),
                }
            )

        # 3. Class Skeleton Chunks
        classes = [s for s in parsed_file.symbols if s.kind in ("class", "interface", "struct")]
        for cls_sym in classes:
            child_symbols = [
                s for s in parsed_file.symbols if s.parent == cls_sym.name and s.kind == "method"
            ]
            skel_lines = [f"{cls_sym.signature}:"]
            if cls_sym.docstring:
                skel_lines.append(f'    """{cls_sym.docstring}"""')
            for m in child_symbols:
                m_doc = f" -- {m.docstring.splitlines()[0]}" if m.docstring else ""
                skel_lines.append(f"    {m.signature}{m_doc}")

            skel_text = escape_source_delimiters("\n".join(skel_lines))
            c_header = self.build_contextual_header(
                path=path,
                language=lang,
                symbol=cls_sym,
                imports=parsed_file.imports,
            )
            embed_text = f"{c_header}\n\n{skel_text}"
            token_count = self.count_tokens(embed_text)

            chunks.append(
                {
                    "_id": f"{repo_id}:{path}:{cls_sym.name}:skeleton",
                    "repo_id": repo_id,
                    "commit_sha": commit_sha,
                    "path": path,
                    "language": lang,
                    "chunk_type": "class_skeleton",
                    "symbol_name": cls_sym.name,
                    "symbol_kind": cls_sym.kind,
                    "parent_symbol": None,
                    "start_line": cls_sym.start_line,
                    "end_line": cls_sym.end_line,
                    "part": 1,
                    "parts": 1,
                    "text": skel_text,
                    "embed_text": embed_text,
                    "token_count": token_count,
                    "content_hash": self.compute_hash(skel_text),
                }
            )

        # 4. Symbol Chunks (function, method, component, or docs/config sections)
        callable_symbols = [
            s
            for s in parsed_file.symbols
            if s.kind in ("function", "method", "component", "section", "const")
        ]

        # If no symbols extracted (e.g. fallback or empty), use fallback windows
        if not callable_symbols and total_lines > 0:
            window_size = 60
            overlap = 10
            start = 1
            idx = 1
            while start <= total_lines:
                end = min(total_lines, start + window_size - 1)
                chunk_lines = source_lines[start - 1 : end]
                text = escape_source_delimiters("\n".join(chunk_lines))
                c_header = self.build_contextual_header(
                    path=path, language=lang, imports=parsed_file.imports
                )
                embed_text = f"{c_header}\n\n{text}"
                token_count = self.count_tokens(embed_text)

                chunks.append(
                    {
                        "_id": f"{repo_id}:{path}:L{start}-L{end}",
                        "repo_id": repo_id,
                        "commit_sha": commit_sha,
                        "path": path,
                        "language": lang,
                        "chunk_type": "code",
                        "symbol_name": None,
                        "symbol_kind": None,
                        "parent_symbol": None,
                        "start_line": start,
                        "end_line": end,
                        "part": 1,
                        "parts": 1,
                        "text": text,
                        "embed_text": embed_text,
                        "token_count": token_count,
                        "content_hash": self.compute_hash(text),
                    }
                )
                if end >= total_lines:
                    break
                start += max(1, window_size - overlap)
                idx += 1

        for sym in callable_symbols:
            start_l = max(1, sym.start_line)
            end_l = min(total_lines, max(start_l, sym.end_line))
            sym_lines = source_lines[start_l - 1 : end_l]
            raw_text = "\n".join(sym_lines)
            tokens = self.count_tokens(raw_text)

            chunk_kind = "doc" if sym.kind == "section" else "code"

            # Check if large symbol (> 800 tokens) -> split into <= 512 token parts with 3-line overlap
            if tokens > 800 and len(sym_lines) > 10:
                parts: list[tuple[int, int, str]] = []  # (sub_start, sub_end, sub_text)
                cur_lines: list[str] = []
                sub_start = start_l
                line_idx = 0

                while line_idx < len(sym_lines):
                    cur_lines.append(sym_lines[line_idx])
                    cur_text = "\n".join(cur_lines)
                    cur_tokens = self.count_tokens(cur_text)

                    # When exceeding 512 tokens or reached end
                    if cur_tokens >= 500 or line_idx == len(sym_lines) - 1:
                        sub_end = start_l + line_idx
                        parts.append((sub_start, sub_end, cur_text))

                        if line_idx == len(sym_lines) - 1:
                            break

                        # Overlap: keep last 3 lines
                        overlap_lines = cur_lines[-3:] if len(cur_lines) >= 3 else cur_lines
                        cur_lines = list(overlap_lines)
                        sub_start = sub_end - len(overlap_lines) + 1

                    line_idx += 1

                total_parts = len(parts)
                for p_idx, (p_start, p_end, p_text) in enumerate(parts, 1):
                    esc_text = escape_source_delimiters(p_text)
                    c_header = self.build_contextual_header(
                        path=path,
                        language=lang,
                        symbol=sym,
                        imports=parsed_file.imports,
                    )
                    embed_text = f"{c_header} (part {p_idx}/{total_parts})\n\n{esc_text}"
                    t_count = self.count_tokens(embed_text)

                    cid = f"{repo_id}:{path}:{sym.qualified_name}:p{p_idx}"
                    sym.chunk_ids.append(cid)
                    chunks.append(
                        {
                            "_id": cid,
                            "repo_id": repo_id,
                            "commit_sha": commit_sha,
                            "path": path,
                            "language": lang,
                            "chunk_type": chunk_kind,
                            "symbol_name": sym.name,
                            "symbol_kind": sym.kind,
                            "parent_symbol": sym.parent,
                            "start_line": p_start,
                            "end_line": p_end,
                            "part": p_idx,
                            "parts": total_parts,
                            "text": esc_text,
                            "embed_text": embed_text,
                            "token_count": t_count,
                            "content_hash": self.compute_hash(esc_text),
                        }
                    )
            else:
                esc_text = escape_source_delimiters(raw_text)
                c_header = self.build_contextual_header(
                    path=path,
                    language=lang,
                    symbol=sym,
                    imports=parsed_file.imports,
                )
                embed_text = f"{c_header}\n\n{esc_text}"
                t_count = self.count_tokens(embed_text)

                cid = f"{repo_id}:{path}:{sym.qualified_name}"
                sym.chunk_ids.append(cid)
                chunks.append(
                    {
                        "_id": cid,
                        "repo_id": repo_id,
                        "commit_sha": commit_sha,
                        "path": path,
                        "language": lang,
                        "chunk_type": chunk_kind,
                        "symbol_name": sym.name,
                        "symbol_kind": sym.kind,
                        "parent_symbol": sym.parent,
                        "start_line": start_l,
                        "end_line": end_l,
                        "part": 1,
                        "parts": 1,
                        "text": esc_text,
                        "embed_text": embed_text,
                        "token_count": t_count,
                        "content_hash": self.compute_hash(esc_text),
                    }
                )

        return chunks

    def build_directory_summaries(
        self,
        parsed_files: list[ParsedFile],
        repo_id: str,
        commit_sha: str,
    ) -> list[dict[str, Any]]:
        """
        Builds directory summary chunks (§8.5):
        For each directory with >= 2 indexed files: file list + their card first lines.
        """
        dir_to_files: dict[str, list[ParsedFile]] = defaultdict(list)
        for pf in parsed_files:
            parts = pf.path.split("/")
            if len(parts) > 1:
                dir_path = "/".join(parts[:-1])
            else:
                dir_path = "."
            dir_to_files[dir_path].append(pf)

        summary_chunks: list[dict[str, Any]] = []

        for dir_path, files in dir_to_files.items():
            if len(files) < 2:
                continue

            lines = [f"# Directory: {dir_path}", f"Files ({len(files)}):"]
            for f in sorted(files, key=lambda x: x.path):
                first_summary = "Source file"
                if f.module_docstring:
                    first_summary = f.module_docstring.strip().splitlines()[0]
                elif f.card:
                    for cline in f.card.splitlines():
                        if cline.startswith("Summary:"):
                            first_summary = cline.replace("Summary:", "").strip()
                            break
                lines.append(f"  - {f.path} ({f.language}): {first_summary}")

            text = escape_source_delimiters("\n".join(lines))
            embed_text = f"Directory Summary: {dir_path}\n\n{text}"
            token_count = self.count_tokens(embed_text)

            cid = f"{repo_id}:dir_summary:{dir_path}"
            summary_chunks.append(
                {
                    "_id": cid,
                    "repo_id": repo_id,
                    "commit_sha": commit_sha,
                    "path": dir_path,
                    "language": "markdown",
                    "chunk_type": "dir_summary",
                    "symbol_name": None,
                    "symbol_kind": None,
                    "parent_symbol": None,
                    "start_line": 1,
                    "end_line": max(1, len(lines)),
                    "part": 1,
                    "parts": 1,
                    "text": text,
                    "embed_text": embed_text,
                    "token_count": token_count,
                    "content_hash": self.compute_hash(text),
                }
            )

        return summary_chunks
