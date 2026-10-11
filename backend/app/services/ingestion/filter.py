"""
File filtering, language detection, and classification engine (§8.2).
Applies default ignores, .gitignore, binary detection, size limits, and minified heuristics.
"""

import hashlib
import os
from pathlib import PurePosixPath
from typing import Any

import pathspec
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Default ignored directories
DEFAULT_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "out",
    "target",
    ".next",
    ".nuxt",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "bin",
    "obj",
}

# Default ignored filenames (exact matches)
DEFAULT_IGNORED_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "cargo.lock",
    "go.sum",
    "composer.lock",
    "gemfile.lock",
}

# Default ignored binary / media extensions
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".svg",
    ".bmp",
    ".tiff",
    ".mp3",
    ".wav",
    ".ogg",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".jar",
    ".war",
    ".ear",
    ".wasm",
    ".pyc",
    ".pyo",
    ".pyd",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".db",
    ".sqlite",
    ".sqlite3",
}

# Extension to language map
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".java": "java",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".cs": "csharp",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".less": "css",
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "rst",
    ".adoc": "asciidoc",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".env.example": "config",
}

# Filename to language / kind overrides
FILENAME_LANGUAGE_MAP: dict[str, str] = {
    "dockerfile": "dockerfile",
    "containerfile": "dockerfile",
    "makefile": "makefile",
    "gemfile": "ruby",
    "rakefile": "ruby",
    "vagrantfile": "ruby",
    "cmakelists.txt": "cmake",
}

DOC_LANGUAGES = {"markdown", "rst", "asciidoc", "text"}
CONFIG_LANGUAGES = {"json", "yaml", "toml", "ini", "dockerfile", "makefile", "config"}


def detect_language(path_str: str) -> str:
    """Detects programming language or markup format by file extension or name."""
    posix = PurePosixPath(path_str.replace("\\", "/"))
    filename_lower = posix.name.lower()
    if filename_lower in FILENAME_LANGUAGE_MAP:
        return FILENAME_LANGUAGE_MAP[filename_lower]

    suffix = posix.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(suffix, "generic")


def classify_file_kind(path_str: str, language: str) -> str:
    """
    Classifies file into kind: 'code' | 'doc' | 'config' | 'test'.
    """
    posix = PurePosixPath(path_str.replace("\\", "/"))
    parts_lower = [p.lower() for p in posix.parts]
    filename_lower = posix.name.lower()

    # Test classification
    if (
        "test" in parts_lower
        or "tests" in parts_lower
        or "__tests__" in parts_lower
        or filename_lower.startswith("test_")
        or filename_lower.endswith("_test.py")
        or filename_lower.endswith("_test.go")
        or ".test." in filename_lower
        or ".spec." in filename_lower
    ):
        return "test"

    if language in DOC_LANGUAGES:
        return "doc"
    if language in CONFIG_LANGUAGES:
        return "config"
    return "code"


def is_binary_file(file_path: str) -> bool:
    """Checks for presence of NUL bytes in the first 8 KB or invalid text decoding."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
            try:
                chunk.decode("utf-8")
                return False
            except UnicodeDecodeError:
                # Try fallback decoding
                import charset_normalizer

                match = charset_normalizer.from_bytes(chunk).best()
                return match is None
    except Exception:
        return True


def is_minified_or_generated(lines: list[str]) -> tuple[bool, str]:
    """
    Heuristics to detect minified bundles or auto-generated code.
    Returns (is_minified_or_generated, reason).
    """
    if not lines:
        return False, ""

    # Check for average line length > 300
    total_len = sum(len(line) for line in lines)
    avg_len = total_len / len(lines)
    if avg_len > 300:
        return True, "minified"

    # Check first 5 lines for auto-generation markers
    markers = [
        "auto-generated",
        "autogenerated",
        "do not edit",
        "generated by",
        "code generated by",
        "@generated",
    ]
    header = "\n".join(lines[:5]).lower()
    for marker in markers:
        if marker in header:
            return True, "generated"

    return False, ""


class IngestionFilter:
    def __init__(self, root_dir: str, extra_ignore_patterns: list[str] | None = None) -> None:
        self.root_dir = os.path.abspath(root_dir)
        self.settings = get_settings()
        self.max_file_size_bytes = self.settings.MAX_FILE_SIZE_KB * 1024
        self.max_files = self.settings.MAX_FILES

        # Build gitignore matcher
        ignore_lines = []
        gitignore_path = os.path.join(self.root_dir, ".gitignore")
        if os.path.isfile(gitignore_path):
            with open(gitignore_path, encoding="utf-8", errors="ignore") as f:
                ignore_lines.extend(f.readlines())

        repogptignore_path = os.path.join(self.root_dir, ".repogptignore")
        if os.path.isfile(repogptignore_path):
            with open(repogptignore_path, encoding="utf-8", errors="ignore") as f:
                ignore_lines.extend(f.readlines())

        if extra_ignore_patterns:
            ignore_lines.extend(extra_ignore_patterns)

        self.path_spec = (
            pathspec.PathSpec.from_lines("gitwildmatch", ignore_lines) if ignore_lines else None
        )

    def scan_and_filter(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Scans root_dir recursively and applies filtering pipeline in order (§8.2).
        Returns (valid_files, skipped_files).
        """
        valid_candidates: list[dict[str, Any]] = []
        skipped_files: list[dict[str, Any]] = []

        for root, dirs, files in os.walk(self.root_dir):
            rel_root = os.path.relpath(root, self.root_dir).replace("\\", "/")
            if rel_root == ".":
                rel_root = ""

            # Filter out ignored directories in-place
            dirs[:] = [
                d
                for d in dirs
                if d not in DEFAULT_IGNORED_DIRS
                and not (
                    self.path_spec
                    and self.path_spec.match_file(f"{rel_root}/{d}" if rel_root else d)
                )
            ]

            for fname in files:
                rel_path = f"{rel_root}/{fname}" if rel_root else fname
                full_path = os.path.join(root, fname)
                posix = PurePosixPath(rel_path)

                # 1. Default ignores
                if fname.lower() in DEFAULT_IGNORED_FILES:
                    skipped_files.append(
                        {
                            "path": rel_path,
                            "reason": "ignored",
                            "size_bytes": os.path.getsize(full_path),
                        }
                    )
                    continue

                if (
                    fname.endswith(".min.js")
                    or fname.endswith(".min.css")
                    or fname.endswith(".map")
                ):
                    skipped_files.append(
                        {
                            "path": rel_path,
                            "reason": "minified",
                            "size_bytes": os.path.getsize(full_path),
                        }
                    )
                    continue

                if posix.suffix.lower() in BINARY_EXTENSIONS:
                    skipped_files.append(
                        {
                            "path": rel_path,
                            "reason": "binary",
                            "size_bytes": os.path.getsize(full_path),
                        }
                    )
                    continue

                # 2. PathSpec gitignore
                if self.path_spec and self.path_spec.match_file(rel_path):
                    skipped_files.append(
                        {
                            "path": rel_path,
                            "reason": "ignored",
                            "size_bytes": os.path.getsize(full_path),
                        }
                    )
                    continue

                try:
                    file_size = os.path.getsize(full_path)
                except OSError:
                    continue

                # 3. File size cap
                if file_size > self.max_file_size_bytes:
                    skipped_files.append(
                        {"path": rel_path, "reason": "too_large", "size_bytes": file_size}
                    )
                    continue

                # 4. Binary check
                if is_binary_file(full_path):
                    skipped_files.append(
                        {"path": rel_path, "reason": "binary", "size_bytes": file_size}
                    )
                    continue

                # Read lines and check minified/generated
                try:
                    with open(full_path, encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except Exception:
                    skipped_files.append(
                        {"path": rel_path, "reason": "binary", "size_bytes": file_size}
                    )
                    continue

                # 5. Minified/generated heuristic
                is_gen, gen_reason = is_minified_or_generated(lines)
                if is_gen:
                    skipped_files.append(
                        {"path": rel_path, "reason": gen_reason, "size_bytes": file_size}
                    )
                    continue

                # 6. Language and Kind
                language = detect_language(rel_path)
                kind = classify_file_kind(rel_path, language)

                # Compute SHA-256 content hash
                content_bytes = "".join(lines).encode("utf-8")
                content_hash = hashlib.sha256(content_bytes).hexdigest()

                # Priority score for truncation (higher = prioritize keeping)
                priority = 0
                if kind in ("doc", "config"):
                    priority += 30
                elif language in ("python", "javascript", "typescript", "java", "go"):
                    priority += 20
                else:
                    priority += 10
                # Shallower depth gives higher priority
                depth = len(posix.parts)
                priority -= depth

                valid_candidates.append(
                    {
                        "path": rel_path,
                        "language": language,
                        "kind": kind,
                        "size_bytes": file_size,
                        "loc": len(lines),
                        "content_hash": content_hash,
                        "priority": priority,
                    }
                )

        # 7. Cap by MAX_FILES
        if len(valid_candidates) > self.max_files:
            logger.warning(
                "repo_file_limit_exceeded",
                total=len(valid_candidates),
                limit=self.max_files,
            )
            # Sort by priority descending
            valid_candidates.sort(key=lambda x: x["priority"], reverse=True)
            kept = valid_candidates[: self.max_files]
            truncated = valid_candidates[self.max_files :]
            for t in truncated:
                skipped_files.append(
                    {
                        "path": t["path"],
                        "reason": "limit",
                        "size_bytes": t["size_bytes"],
                    }
                )
            valid_candidates = kept

        # Sort valid candidates deterministically by path
        valid_candidates.sort(key=lambda x: x["path"])
        return valid_candidates, skipped_files
