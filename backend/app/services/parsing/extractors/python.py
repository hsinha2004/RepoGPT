"""
Python AST Extractor using tree-sitter (§8.4).
Extracts functions, classes, methods, docstrings, type annotations, imports, route decorators and entry points.
"""

import structlog
import tree_sitter
import tree_sitter_language_pack as tslp

from app.services.parsing.extractors.base import BaseExtractor
from app.services.parsing.extractors.fallback import FallbackExtractor
from app.services.parsing.models import EntryPointHint, ParsedFile, SymbolInfo

logger = structlog.get_logger(__name__)


class PythonExtractor(BaseExtractor):
    def __init__(self) -> None:
        self.parser: tree_sitter.Parser | None = None
        try:
            self.parser = tslp.get_parser("python")
        except Exception as e:
            logger.warning("python_parser_init_failed", error=str(e))
            self.parser = None

    def extract(self, source: str, path: str = "") -> ParsedFile:
        if not self.parser:
            try:
                self.parser = tslp.get_parser("python")
            except Exception:
                self.parser = None
        if not self.parser:
            return FallbackExtractor().extract(source, path)

        try:
            source_bytes = source.encode("utf-8")
            tree = self.parser.parse(source_bytes)
            root = tree.root_node
        except Exception as e:
            logger.warning("python_parse_failed", path=path, error=str(e))
            return FallbackExtractor().extract(source, path)

        symbols: list[SymbolInfo] = []
        imports: list[str] = []
        entry_point_hints: list[EntryPointHint] = []
        top_level_ranges: list[tuple[int, int]] = []
        module_docstring: str | None = None

        def get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

        def extract_docstring(block_node: tree_sitter.Node | None) -> str | None:
            if not block_node:
                return None
            for child in block_node.children:
                if child.type == "string":
                    raw = get_node_text(child)
                    for q in ('"""', "'''", '"', "'"):
                        if raw.startswith(q) and raw.endswith(q) and len(raw) >= 2 * len(q):
                            return raw[len(q) : -len(q)].strip()
                    return raw.strip()
                elif child.type == "expression_statement":
                    for sub in child.children:
                        if sub.type == "string":
                            raw = get_node_text(sub)
                            # Strip quotes
                            for q in ('"""', "'''", '"', "'"):
                                if raw.startswith(q) and raw.endswith(q) and len(raw) >= 2 * len(q):
                                    return raw[len(q) : -len(q)].strip()
                            return raw.strip()
                elif child.type not in ("comment", "\n"):
                    break
            return None

        # Check module docstring
        for child in root.children:
            if child.type == "string":
                raw = get_node_text(child)
                for q in ('"""', "'''", '"', "'"):
                    if raw.startswith(q) and raw.endswith(q) and len(raw) >= 2 * len(q):
                        module_docstring = raw[len(q) : -len(q)].strip()
                        break
                if not module_docstring:
                    module_docstring = raw.strip()
                break
            elif child.type == "expression_statement":
                for sub in child.children:
                    if sub.type == "string":
                        raw = get_node_text(sub)
                        for q in ('"""', "'''", '"', "'"):
                            if raw.startswith(q) and raw.endswith(q) and len(raw) >= 2 * len(q):
                                module_docstring = raw[len(q) : -len(q)].strip()
                                break
                        if not module_docstring:
                            module_docstring = raw.strip()
                        break
                if module_docstring:
                    break
            elif child.type not in ("comment", "\n"):
                break

        def process_function(
            fn_node: tree_sitter.Node,
            parent_class: str | None = None,
            decorators: list[str] | None = None,
        ) -> SymbolInfo:
            decorators = decorators or []
            name_node = fn_node.child_by_field_name("name")
            name = get_node_text(name_node) if name_node else "anonymous"

            params_node = fn_node.child_by_field_name("parameters")
            params = get_node_text(params_node) if params_node else "()"

            return_type_node = fn_node.child_by_field_name("return_type")
            return_type = f" -> {get_node_text(return_type_node)}" if return_type_node else ""

            is_async = any(c.type == "async" for c in fn_node.children)
            prefix = "async def " if is_async else "def "

            dec_str = " ".join(f"@{d}" for d in decorators) + " " if decorators else ""
            signature = f"{dec_str}{prefix}{name}{params}{return_type}"

            body_node = fn_node.child_by_field_name("body")
            doc = extract_docstring(body_node)

            start_line = fn_node.start_point[0] + 1
            end_line = fn_node.end_point[0] + 1

            kind = "method" if parent_class else "function"
            qualified_name = f"{parent_class}.{name}" if parent_class else name

            # Route decorator hints
            for dec in decorators:
                if any(
                    r in dec.lower()
                    for r in [
                        "get",
                        "post",
                        "put",
                        "delete",
                        "patch",
                        "route",
                        "api_view",
                        "endpoint",
                    ]
                ):
                    entry_point_hints.append(
                        EntryPointHint(
                            reason=f"Route handler @{dec}",
                            line=start_line,
                            symbol=qualified_name,
                        )
                    )

            return SymbolInfo(
                name=name,
                qualified_name=qualified_name,
                kind=kind,
                signature=signature,
                start_line=start_line,
                end_line=end_line,
                language="python",
                docstring=doc,
                parent=parent_class,
                exported=not name.startswith("_"),
            )

        def process_class(
            cls_node: tree_sitter.Node,
            decorators: list[str] | None = None,
        ) -> tuple[SymbolInfo, list[SymbolInfo]]:
            decorators = decorators or []
            name_node = cls_node.child_by_field_name("name")
            name = get_node_text(name_node) if name_node else "AnonymousClass"

            superclasses_node = cls_node.child_by_field_name("superclasses")
            superclasses = get_node_text(superclasses_node) if superclasses_node else ""

            dec_str = " ".join(f"@{d}" for d in decorators) + " " if decorators else ""
            signature = f"{dec_str}class {name}{superclasses}"

            body_node = cls_node.child_by_field_name("body")
            doc = extract_docstring(body_node)

            start_line = cls_node.start_point[0] + 1
            end_line = cls_node.end_point[0] + 1

            cls_sym = SymbolInfo(
                name=name,
                qualified_name=name,
                kind="class",
                signature=signature,
                start_line=start_line,
                end_line=end_line,
                language="python",
                docstring=doc,
                parent=None,
                exported=not name.startswith("_"),
            )

            methods: list[SymbolInfo] = []
            if body_node:
                child_idx = 0
                body_children = body_node.children
                while child_idx < len(body_children):
                    child = body_children[child_idx]
                    if child.type == "function_definition":
                        methods.append(process_function(child, parent_class=name))
                    elif child.type == "decorated_definition":
                        dec_list: list[str] = []
                        target = None
                        for sub in child.children:
                            if sub.type == "decorator":
                                dec_list.append(get_node_text(sub).lstrip("@").strip())
                            elif sub.type in ("function_definition", "class_definition"):
                                target = sub
                        if target and target.type == "function_definition":
                            methods.append(
                                process_function(target, parent_class=name, decorators=dec_list)
                            )
                    child_idx += 1

            return cls_sym, methods

        # Iterate top-level nodes
        for node in root.children:
            start_l = node.start_point[0] + 1
            end_l = node.end_point[0] + 1

            if node.type == "import_statement":
                # import foo, bar
                for child in node.children:
                    if child.type == "dotted_name":
                        imports.append(get_node_text(child))
                    elif child.type == "aliased_import":
                        name_n = child.child_by_field_name("name")
                        if name_n:
                            imports.append(get_node_text(name_n))
                top_level_ranges.append((start_l, end_l))

            elif node.type == "import_from_statement":
                # from foo import bar
                module_name = ""
                for child in node.children:
                    if child.type in ("dotted_name", "relative_import"):
                        module_name = get_node_text(child)
                        break
                if module_name:
                    imports.append(module_name)
                top_level_ranges.append((start_l, end_l))

            elif node.type == "function_definition":
                sym = process_function(node)
                symbols.append(sym)
                top_level_ranges.append((start_l, end_l))

            elif node.type == "class_definition":
                cls_sym, methods = process_class(node)
                symbols.append(cls_sym)
                symbols.extend(methods)
                top_level_ranges.append((start_l, end_l))

            elif node.type == "decorated_definition":
                dec_list: list[str] = []
                target = None
                for sub in node.children:
                    if sub.type == "decorator":
                        dec_list.append(get_node_text(sub).lstrip("@").strip())
                    elif sub.type in ("function_definition", "class_definition"):
                        target = sub
                if target:
                    if target.type == "function_definition":
                        symbols.append(process_function(target, decorators=dec_list))
                    elif target.type == "class_definition":
                        cls_sym, methods = process_class(target, decorators=dec_list)
                        symbols.append(cls_sym)
                        symbols.extend(methods)
                top_level_ranges.append((start_l, end_l))

            elif node.type == "if_statement":
                # Check for if __name__ == "__main__":
                cond = node.child_by_field_name("condition")
                if cond and "__main__" in get_node_text(cond):
                    entry_point_hints.append(
                        EntryPointHint(
                            reason='Entry point: if __name__ == "__main__"',
                            line=start_l,
                        )
                    )
                top_level_ranges.append((start_l, end_l))

        card = self.build_file_card(
            path=path,
            language="python",
            module_docstring=module_docstring,
            imports=imports,
            symbols=symbols,
        )

        return ParsedFile(
            path=path,
            language="python",
            symbols=symbols,
            imports=sorted(set(imports)),
            module_docstring=module_docstring,
            top_level_ranges=top_level_ranges,
            entry_point_hints=entry_point_hints,
            card=card,
        )
