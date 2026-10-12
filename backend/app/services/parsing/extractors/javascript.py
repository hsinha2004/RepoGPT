"""
JavaScript & TypeScript AST Extractors using tree-sitter (§8.4).
Extracts functions, arrow expressions, classes, methods, React components,
interfaces, types, enums, ESM/CJS imports, and route registration hints.
"""

import re

import structlog
import tree_sitter
import tree_sitter_language_pack as tslp

from app.services.parsing.extractors.base import BaseExtractor
from app.services.parsing.extractors.fallback import FallbackExtractor
from app.services.parsing.models import EntryPointHint, ParsedFile, SymbolInfo

logger = structlog.get_logger(__name__)


class JavascriptExtractor(BaseExtractor):
    def __init__(self, language_name: str = "javascript") -> None:
        self.language_name = language_name
        try:
            self.parser = tslp.get_parser(language_name)
        except Exception as e:
            logger.warning("javascript_parser_init_failed", language=language_name, error=str(e))
            self.parser = None

    def extract(self, source: str, path: str = "") -> ParsedFile:
        if not self.parser:
            try:
                self.parser = tslp.get_parser(self.language_name)
            except Exception:
                self.parser = None
        if not self.parser:
            return FallbackExtractor().extract(source, path)

        try:
            source_bytes = source.encode("utf-8")
            tree = self.parser.parse(source_bytes)
            root = tree.root_node
        except Exception as e:
            logger.warning("javascript_parse_failed", path=path, error=str(e))
            return FallbackExtractor().extract(source, path)

        symbols: list[SymbolInfo] = []
        imports: list[str] = []
        entry_point_hints: list[EntryPointHint] = []
        top_level_ranges: list[tuple[int, int]] = []
        module_docstring: str | None = None

        def get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

        def extract_leading_jsdoc(node: tree_sitter.Node) -> str | None:
            prev = node.prev_named_sibling
            if prev and prev.type == "comment":
                raw = get_node_text(prev).strip()
                if raw.startswith("/**") and raw.endswith("*/"):
                    # Strip JSDoc delimiters and * prefixes
                    lines = raw[3:-2].strip().splitlines()
                    clean = [re.sub(r"^\s*\*\s?", "", line).strip() for line in lines]
                    return "\n".join(clean).strip()
                return raw.lstrip("/").strip()
            return None

        def is_jsx_present(node: tree_sitter.Node) -> bool:
            """Recursively checks if node contains JSX elements."""
            if "jsx" in node.type:
                return True
            for child in node.children:
                if is_jsx_present(child):
                    return True
            return False

        def clean_string_literal(text: str) -> str:
            return text.strip("'\"`")

        def process_class(
            cls_node: tree_sitter.Node,
            exported: bool = False,
        ) -> tuple[SymbolInfo, list[SymbolInfo]]:
            name_node = cls_node.child_by_field_name("name")
            name = get_node_text(name_node) if name_node else "AnonymousClass"

            heritage = ""
            for child in cls_node.children:
                if child.type in ("class_heritage", "extends_clause", "implements_clause"):
                    heritage = f" {get_node_text(child)}"

            signature = f"class {name}{heritage}"
            doc = extract_leading_jsdoc(cls_node)
            start_l = cls_node.start_point[0] + 1
            end_l = cls_node.end_point[0] + 1

            cls_sym = SymbolInfo(
                name=name,
                qualified_name=name,
                kind="class",
                signature=signature,
                start_line=start_l,
                end_line=end_l,
                language=self.language_name,
                docstring=doc,
                parent=None,
                exported=exported,
            )

            methods: list[SymbolInfo] = []
            body_node = cls_node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    if child.type == "method_definition":
                        m_name_node = child.child_by_field_name("name")
                        m_name = get_node_text(m_name_node) if m_name_node else "method"
                        m_params = child.child_by_field_name("parameters")
                        m_sig_params = get_node_text(m_params) if m_params else "()"
                        m_doc = extract_leading_jsdoc(child)
                        m_start = child.start_point[0] + 1
                        m_end = child.end_point[0] + 1
                        methods.append(
                            SymbolInfo(
                                name=m_name,
                                qualified_name=f"{name}.{m_name}",
                                kind="method",
                                signature=f"{m_name}{m_sig_params}",
                                start_line=m_start,
                                end_line=m_end,
                                language=self.language_name,
                                docstring=m_doc,
                                parent=name,
                                exported=exported and not m_name.startswith("#"),
                            )
                        )
            return cls_sym, methods

        def traverse_node(node: tree_sitter.Node, exported: bool = False) -> None:
            start_l = node.start_point[0] + 1
            end_l = node.end_point[0] + 1

            # Check for route registration call hints: app.get('/...', ...), router.post(...)
            if node.type == "call_expression":
                fn_node = node.child_by_field_name("function")
                if fn_node and fn_node.type == "member_expression":
                    prop_n = fn_node.child_by_field_name("property")
                    prop = get_node_text(prop_n) if prop_n else ""
                    if prop.lower() in ("get", "post", "put", "delete", "patch", "use"):
                        obj_n = fn_node.child_by_field_name("object")
                        obj = get_node_text(obj_n) if obj_n else ""
                        if obj.lower() in ("app", "router", "server", "api"):
                            entry_point_hints.append(
                                EntryPointHint(
                                    reason=f"Express route registration: {obj}.{prop}",
                                    line=start_l,
                                )
                            )

            # Expression Statement (e.g. app.get(...), function calls)
            if node.type == "expression_statement":
                for child in node.children:
                    traverse_node(child, exported=exported)
                top_level_ranges.append((start_l, end_l))
                return

            # ESM Imports: import ... from '...'
            if node.type == "import_statement":
                source_n = node.child_by_field_name("source")
                if source_n:
                    imports.append(clean_string_literal(get_node_text(source_n)))
                top_level_ranges.append((start_l, end_l))
                return

            # CJS require: const x = require('...')
            if node.type == "call_expression":
                fn_node = node.child_by_field_name("function")
                if fn_node and get_node_text(fn_node) in ("require", "import"):
                    args = node.child_by_field_name("arguments")
                    if args and args.children:
                        first_arg = args.children[1] if len(args.children) > 1 else None
                        if first_arg and first_arg.type == "string":
                            imports.append(clean_string_literal(get_node_text(first_arg)))

            # Export Statement
            if node.type == "export_statement":
                # export { x } from '...'
                source_n = node.child_by_field_name("source")
                if source_n:
                    imports.append(clean_string_literal(get_node_text(source_n)))

                for child in node.children:
                    if child.type in (
                        "function_declaration",
                        "generator_function_declaration",
                        "class_declaration",
                        "lexical_declaration",
                        "variable_declaration",
                        "interface_declaration",
                        "type_alias_declaration",
                        "enum_declaration",
                    ):
                        traverse_node(child, exported=True)
                top_level_ranges.append((start_l, end_l))
                return

            # Function Declaration
            if node.type in ("function_declaration", "generator_function_declaration"):
                name_n = node.child_by_field_name("name")
                name = get_node_text(name_n) if name_n else "anonymous"
                params_n = node.child_by_field_name("parameters")
                params = get_node_text(params_n) if params_n else "()"
                return_type_n = node.child_by_field_name("return_type")
                return_type = f": {get_node_text(return_type_n)}" if return_type_n else ""
                signature = f"function {name}{params}{return_type}"
                doc = extract_leading_jsdoc(node)

                # Check if React component: PascalCase and returns/contains JSX
                body_n = node.child_by_field_name("body")
                kind = "function"
                if name and name[0].isupper() and body_n and is_jsx_present(body_n):
                    kind = "component"

                symbols.append(
                    SymbolInfo(
                        name=name,
                        qualified_name=name,
                        kind=kind,
                        signature=signature,
                        start_line=start_l,
                        end_line=end_l,
                        language=self.language_name,
                        docstring=doc,
                        parent=None,
                        exported=exported,
                    )
                )
                top_level_ranges.append((start_l, end_l))
                return

            # Class Declaration
            if node.type in ("class_declaration", "abstract_class_declaration"):
                cls_sym, methods = process_class(node, exported=exported)
                symbols.append(cls_sym)
                symbols.extend(methods)
                top_level_ranges.append((start_l, end_l))
                return

            # Lexical / Variable Declarations: const fn = () => ... or const Component = () => <JSX />
            if node.type in ("lexical_declaration", "variable_declaration"):
                for declarator in node.children:
                    if declarator.type == "variable_declarator":
                        name_n = declarator.child_by_field_name("name")
                        value_n = declarator.child_by_field_name("value")
                        if name_n and value_n:
                            name = get_node_text(name_n)
                            val_type = value_n.type
                            doc = extract_leading_jsdoc(node)

                            if val_type == "call_expression":
                                fn_node = value_n.child_by_field_name("function")
                                if fn_node and get_node_text(fn_node) in ("require", "import"):
                                    args = value_n.child_by_field_name("arguments")
                                    if args and args.children:
                                        for arg_child in args.children:
                                            if arg_child.type == "string":
                                                imports.append(
                                                    clean_string_literal(get_node_text(arg_child))
                                                )

                            elif val_type in ("arrow_function", "function_expression"):
                                params_n = value_n.child_by_field_name("parameters")
                                params = get_node_text(params_n) if params_n else "()"
                                ret_type_n = value_n.child_by_field_name("return_type")
                                ret_type = f": {get_node_text(ret_type_n)}" if ret_type_n else ""
                                signature = f"const {name} = {params}{ret_type} => ..."

                                kind = "function"
                                body_n = value_n.child_by_field_name("body")
                                if name and name[0].isupper() and body_n and is_jsx_present(body_n):
                                    kind = "component"

                                symbols.append(
                                    SymbolInfo(
                                        name=name,
                                        qualified_name=name,
                                        kind=kind,
                                        signature=signature,
                                        start_line=start_l,
                                        end_line=end_l,
                                        language=self.language_name,
                                        docstring=doc,
                                        parent=None,
                                        exported=exported,
                                    )
                                )

                top_level_ranges.append((start_l, end_l))
                return

            # TypeScript specific nodes
            if node.type == "interface_declaration":
                name_n = node.child_by_field_name("name")
                name = get_node_text(name_n) if name_n else "Interface"
                signature = f"interface {name}"
                doc = extract_leading_jsdoc(node)
                symbols.append(
                    SymbolInfo(
                        name=name,
                        qualified_name=name,
                        kind="interface",
                        signature=signature,
                        start_line=start_l,
                        end_line=end_l,
                        language=self.language_name,
                        docstring=doc,
                        parent=None,
                        exported=exported,
                    )
                )
                top_level_ranges.append((start_l, end_l))
                return

            if node.type == "type_alias_declaration":
                name_n = node.child_by_field_name("name")
                name = get_node_text(name_n) if name_n else "Type"
                signature = f"type {name}"
                doc = extract_leading_jsdoc(node)
                symbols.append(
                    SymbolInfo(
                        name=name,
                        qualified_name=name,
                        kind="type",
                        signature=signature,
                        start_line=start_l,
                        end_line=end_l,
                        language=self.language_name,
                        docstring=doc,
                        parent=None,
                        exported=exported,
                    )
                )
                top_level_ranges.append((start_l, end_l))
                return

            if node.type == "enum_declaration":
                name_n = node.child_by_field_name("name")
                name = get_node_text(name_n) if name_n else "Enum"
                signature = f"enum {name}"
                doc = extract_leading_jsdoc(node)
                symbols.append(
                    SymbolInfo(
                        name=name,
                        qualified_name=name,
                        kind="enum",
                        signature=signature,
                        start_line=start_l,
                        end_line=end_l,
                        language=self.language_name,
                        docstring=doc,
                        parent=None,
                        exported=exported,
                    )
                )
                top_level_ranges.append((start_l, end_l))
                return

        for child in root.children:
            traverse_node(child, exported=False)

        card = self.build_file_card(
            path=path,
            language=self.language_name,
            module_docstring=module_docstring,
            imports=imports,
            symbols=symbols,
        )

        return ParsedFile(
            path=path,
            language=self.language_name,
            symbols=symbols,
            imports=sorted(set(imports)),
            module_docstring=module_docstring,
            top_level_ranges=top_level_ranges,
            entry_point_hints=entry_point_hints,
            card=card,
        )
