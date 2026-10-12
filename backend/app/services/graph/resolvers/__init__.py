from __future__ import annotations

from app.services.graph.resolvers.base import ImportResolver
from app.services.graph.resolvers.go import GoImportResolver
from app.services.graph.resolvers.java import JavaImportResolver
from app.services.graph.resolvers.javascript import JavaScriptImportResolver
from app.services.graph.resolvers.python import PythonImportResolver

_PYTHON_RESOLVER = PythonImportResolver()
_JS_RESOLVER = JavaScriptImportResolver()
_JAVA_RESOLVER = JavaImportResolver()
_GO_RESOLVER = GoImportResolver()


def get_import_resolver(language: str) -> ImportResolver | None:
    """Returns the appropriate language-specific import resolver, or None if unsupported."""
    lang = language.lower().strip()
    if lang in ("python", "py"):
        return _PYTHON_RESOLVER
    if lang in ("javascript", "typescript", "tsx", "jsx", "js", "ts"):
        return _JS_RESOLVER
    if lang in ("java",):
        return _JAVA_RESOLVER
    if lang in ("go", "golang"):
        return _GO_RESOLVER
    return None


__all__ = [
    "GoImportResolver",
    "ImportResolver",
    "JavaImportResolver",
    "JavaScriptImportResolver",
    "PythonImportResolver",
    "get_import_resolver",
]
