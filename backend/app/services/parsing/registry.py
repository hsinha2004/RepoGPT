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
        self._fallback = FallbackExtractor()
        self._docs = DocsExtractor()
        self._config = ConfigExtractor()

        # Configure tree-sitter parsers from shared persistent cache if available
        cache_dir = os.environ.get("TREE_SITTER_CACHE_DIR")
        if not cache_dir:
            model_cache = os.environ.get("MODEL_CACHE_DIR", "/models")
            candidate = os.path.join(model_cache, "tree-sitter-cache")
            if os.path.exists(candidate):
                cache_dir = candidate

        if cache_dir and os.path.exists(cache_dir):
            try:
                import tree_sitter_language_pack as tslp
                from tree_sitter_language_pack import PackConfig

                tslp.configure(PackConfig(cache_dir=cache_dir))
            except Exception as e:
                logger.warning("tslp_configure_failed", error=str(e))

        try:
            self._python: BaseExtractor = PythonExtractor()
        except Exception as e:
            logger.warning("python_extractor_init_failed", error=str(e))
            self._python = self._fallback

        try:
            self._javascript: BaseExtractor = JavascriptExtractor()
        except Exception as e:
            logger.warning("javascript_extractor_init_failed", error=str(e))
            self._javascript = self._fallback

        try:
            self._typescript: BaseExtractor = TypescriptExtractor()
        except Exception as e:
            logger.warning("typescript_extractor_init_failed", error=str(e))
            self._typescript = self._fallback

        try:
            self._tsx: BaseExtractor = TypescriptExtractor(is_tsx=True)
        except Exception as e:
            logger.warning("tsx_extractor_init_failed", error=str(e))
            self._tsx = self._fallback

        try:
            self._java: BaseExtractor = JavaExtractor()
        except Exception as e:
            logger.warning("java_extractor_init_failed", error=str(e))
            self._java = self._fallback

        try:
            self._go: BaseExtractor = GoExtractor()
        except Exception as e:
            logger.warning("go_extractor_init_failed", error=str(e))
            self._go = self._fallback

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
