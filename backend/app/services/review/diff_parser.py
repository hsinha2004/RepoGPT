"""
Unified diff parser and patch application engine using unidiff (§10.2).
Pure Python implementation; never requires the git binary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import unidiff


@dataclass
class ParsedHunk:
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    raw_lines: list[str] = field(default_factory=list)
    added_lines: list[tuple[int, str]] = field(default_factory=list)  # (new_line_num, content)
    deleted_lines: list[tuple[int, str]] = field(default_factory=list)  # (old_line_num, content)
    context_lines: list[str] = field(default_factory=list)


@dataclass
class ParsedFileDiff:
    path: str
    old_path: str
    is_added: bool = False
    is_deleted: bool = False
    is_modified: bool = True
    is_binary: bool = False
    hunks: list[ParsedHunk] = field(default_factory=list)
    added_line_count: int = 0
    deleted_line_count: int = 0
    changed_new_lines: list[int] = field(default_factory=list)


RE_HUNK_HEADER = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@"
)


def _parse_diff_resilient(diff_text: str) -> list[ParsedFileDiff]:
    """Resilient fallback parser for unified diffs with loose hunk headers."""
    files: list[ParsedFileDiff] = []
    current_file: ParsedFileDiff | None = None
    current_hunk: ParsedHunk | None = None
    current_new_line = 1
    current_old_line = 1

    lines = diff_text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("--- "):
            old_path = line[4:].strip()
            if old_path.startswith("a/") or old_path.startswith("b/"):
                old_path = old_path[2:]
            # Look ahead for +++
            if i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
                new_path = lines[i + 1][4:].strip()
                if new_path.startswith("b/") or new_path.startswith("a/"):
                    new_path = new_path[2:]
                if new_path == "/dev/null":
                    new_path = old_path
                current_file = ParsedFileDiff(
                    path=new_path,
                    old_path=old_path,
                    is_added=(old_path == "/dev/null"),
                    is_deleted=(new_path == "/dev/null"),
                )
                files.append(current_file)
                i += 2
                continue

        match = RE_HUNK_HEADER.match(line)
        if match and current_file is not None:
            old_start = int(match.group(1))
            old_len = int(match.group(2) or 1)
            new_start = int(match.group(3))
            new_len = int(match.group(4) or 1)

            current_hunk = ParsedHunk(
                old_start=old_start,
                old_length=old_len,
                new_start=new_start,
                new_length=new_len,
            )
            current_file.hunks.append(current_hunk)
            current_new_line = new_start
            current_old_line = old_start
            i += 1
            continue

        if current_hunk is not None and current_file is not None:
            if line.startswith("+"):
                current_hunk.raw_lines.append(line)
                current_hunk.added_lines.append((current_new_line, line[1:]))
                current_file.changed_new_lines.append(current_new_line)
                current_file.added_line_count += 1
                current_new_line += 1
            elif line.startswith("-"):
                current_hunk.raw_lines.append(line)
                current_hunk.deleted_lines.append((current_old_line, line[1:]))
                current_file.deleted_line_count += 1
                current_old_line += 1
            elif line.startswith(" ") or line == "\n":
                current_hunk.raw_lines.append(line)
                current_hunk.context_lines.append(line[1:] if line.startswith(" ") else line)
                current_new_line += 1
                current_old_line += 1

        i += 1

    return files


def parse_unified_diff(diff_text: str) -> list[ParsedFileDiff]:
    """
    Parses a unified diff string into structured file diffs and hunks.
    """
    if not diff_text or not diff_text.strip():
        return []

    try:
        patch_set = unidiff.PatchSet.from_string(diff_text)
    except Exception:
        # Fallback to resilient parser
        return _parse_diff_resilient(diff_text)

    results: list[ParsedFileDiff] = []

    for patched_file in patch_set:
        path = patched_file.target_file
        old_path = patched_file.source_file

        # Clean prefixes like a/ or b/
        if path.startswith("b/"):
            path = path[2:]
        elif path.startswith("a/"):
            path = path[2:]
        if old_path.startswith("a/"):
            old_path = old_path[2:]
        elif old_path.startswith("b/"):
            old_path = old_path[2:]

        # If /dev/null
        if path == "/dev/null":
            path = old_path

        is_added = patched_file.is_added_file
        is_deleted = patched_file.is_removed_file
        is_binary = patched_file.is_binary_file

        file_diff = ParsedFileDiff(
            path=path,
            old_path=old_path,
            is_added=is_added,
            is_deleted=is_deleted,
            is_modified=not (is_added or is_deleted),
            is_binary=is_binary,
            added_line_count=patched_file.added,
            deleted_line_count=patched_file.removed,
        )

        for h in patched_file:
            ph = ParsedHunk(
                old_start=h.source_start,
                old_length=h.source_length,
                new_start=h.target_start,
                new_length=h.target_length,
            )

            current_new_line = h.target_start
            current_old_line = h.source_start

            for line in h:
                line_str = str(line)
                ph.raw_lines.append(line_str)

                if line.is_added:
                    ph.added_lines.append((current_new_line, line.value))
                    file_diff.changed_new_lines.append(current_new_line)
                    current_new_line += 1
                elif line.is_removed:
                    ph.deleted_lines.append((current_old_line, line.value))
                    current_old_line += 1
                elif line.is_context:
                    ph.context_lines.append(line.value)
                    current_new_line += 1
                    current_old_line += 1

            file_diff.hunks.append(ph)

        results.append(file_diff)

    return results


def apply_patch_to_text(original_text: str, file_diff: ParsedFileDiff) -> str:
    """
    Applies the hunks of a ParsedFileDiff to the base file content to generate
    the head file content (§10.2).
    """
    if file_diff.is_deleted:
        return ""

    if file_diff.is_added:
        # Reconstruct new file entirely from added lines in all hunks
        new_lines: list[str] = []
        for hunk in file_diff.hunks:
            for _, content in hunk.added_lines:
                new_lines.append(content)
        return "".join(new_lines) if new_lines else ""

    # Modified file
    orig_lines = original_text.splitlines(keepends=True)
    out_lines: list[str] = []
    orig_idx = 0

    for hunk in file_diff.hunks:
        # Advance unchanged lines before the hunk
        target_idx = hunk.old_start - 1
        while orig_idx < target_idx and orig_idx < len(orig_lines):
            out_lines.append(orig_lines[orig_idx])
            orig_idx += 1

        # Process the hunk lines
        for raw_line in hunk.raw_lines:
            if not raw_line:
                continue
            marker = raw_line[0]
            content = raw_line[1:]
            if not content.endswith("\n") and not raw_line.endswith("\n"):
                content += "\n"

            if marker == " ":
                # Context line: keep
                out_lines.append(content)
                orig_idx += 1
            elif marker == "-":
                # Removed line: skip from original
                orig_idx += 1
            elif marker == "+":
                # Added line: insert
                out_lines.append(content)

    # Append any remaining lines after the last hunk
    while orig_idx < len(orig_lines):
        out_lines.append(orig_lines[orig_idx])
        orig_idx += 1

    return "".join(out_lines)
