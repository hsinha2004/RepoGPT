"""
TypeScript AST Extractor using tree-sitter (§8.4).
Extends JavascriptExtractor to handle TS/TSX with interfaces, type aliases, enums,
abstract classes and TSX component trees.
"""

from app.services.parsing.extractors.javascript import JavascriptExtractor
from app.services.parsing.models import ParsedFile


class TypescriptExtractor(JavascriptExtractor):
    def __init__(self, is_tsx: bool = False) -> None:
        lang_name = "tsx" if is_tsx else "typescript"
        super().__init__(language_name=lang_name)
        self.is_tsx = is_tsx

    def extract(self, source: str, path: str = "") -> ParsedFile:
        # If file is a .tsx file and this instance was initialized for standard TS,
        # dynamically switch or initialize for tsx
        if (path.endswith(".tsx") or path.endswith(".jsx")) and not self.is_tsx:
            tsx_extractor = TypescriptExtractor(is_tsx=True)
            res = tsx_extractor.extract(source, path)
            res.language = "typescript"
            return res

        res = super().extract(source, path)
        res.language = "typescript"
        return res
