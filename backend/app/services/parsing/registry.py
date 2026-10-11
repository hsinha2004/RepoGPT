"""
ParserRegistry wrapping tree-sitter language pack and specialized extractors (§8.4).
Provides routing by file extension / language with robust fallback on parse failure.
"""

import os

import structlog

from app.services.parsing.extractors.base import BaseExtractor
from app.services.parsing.extractors.config import ConfigExtractor
from app.services.parsing.extractors.docs import DocsExtractor
from app.services.parsing.extractors.fallback import FallbackExtractor
from app.services.parsing.extractors.go import GoExtractor
from app.services.parsing.extractors.java import JavaExtractor
from app.services.parsing.extractors.javascript import JavascriptExtractor
from app.services.parsing.extractors.python import PythonExtractor
from app.services.parsing.extractors.typescript import TypescriptExtractor
from app.services.parsing.models import ParsedFile

logger = structlog.get_logger(__name__)


class ParserRegistry:
    def __init__(self) -> None:
        self._python = PythonExtractor()
        self._javascript = JavascriptExtractor()
        self._typescript = TypescriptExtractor()
        self._tsx = TypescriptExtractor(is_tsx=True)
        self._java = JavaExtractor()
        self._go = GoExtractor()
        self._docs = DocsExtractor()
        self._config = ConfigExtractor()
        self._fallback = FallbackExtractor()

    def get_extractor(self, path: str, language: str | None = None) -> BaseExtractor:
        filename = os.path.basename(path).lower()
        ext = os.path.splitext(filename)[1].lower()

        # Config files by filename
        if filename in (
            "dockerfile",
            "makefile",
            "docker-compose.yml",
            "docker-compose.yaml",
            ".env.example",
        ) or filename.startswith("dockerfile."):
            return self._config

        # Check by extension
        if ext in (".py", ".pyi"):
            return self._python
        elif ext in (".js", ".mjs", ".cjs", ".jsx"):
            return self._javascript
        elif ext in (".tsx",):
            return self._tsx
        elif ext in (".ts", ".mts", ".cts"):
            return self._typescript
        elif ext in (".java",):
            return self._java
        elif ext in (".go",):
            return self._go
        elif ext in (".md", ".mdx", ".rst", ".adoc", ".txt"):
            return self._docs
        elif ext in (".json", ".yml", ".yaml", ".toml"):
            return self._config

        # Check by explicit language
        if language:
            lang = language.lower()
            if lang == "python":
                return self._python
            elif lang in ("javascript", "jsx"):
                return self._javascript
            elif lang in ("typescript", "tsx"):
                return self._typescript
            elif lang == "java":
                return self._java
            elif lang == "go":
                return self._go
            elif lang in ("markdown", "doc", "docs"):
                return self._docs
            elif lang in ("json", "yaml", "config"):
                return self._config

        return self._fallback

    def parse_file(
        self,
        source: str,
        path: str,
        language: str | None = None,
    ) -> ParsedFile:
        """
        Parses source code into structured AST symbols, imports, and docstrings.
        Never fails: if parsing raises an exception, logs warning and falls back to line windows.
        """
        extractor = self.get_extractor(path, language)
        try:
            return extractor.extract(source, path)
        except Exception as e:
            logger.warning(
                "ast_parse_error_fallback",
                path=path,
                extractor=extractor.__class__.__name__,
                error=str(e),
            )
            fallback_res = self._fallback.extract(source, path)
            fallback_res.warnings.append(
                f"Parse error in {path} ({e}); fell back to line-window chunking."
            )
            return fallback_res
