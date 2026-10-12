"""
Java AST Extractor using tree-sitter (§8.4).
Extracts package, imports, classes, interfaces, enums, records, methods, constructors,
annotations (@RestController, @GetMapping) and main entry points.
"""

import structlog
import tree_sitter
import tree_sitter_language_pack as tslp

from app.services.parsing.extractors.base import BaseExtractor
from app.services.parsing.extractors.fallback import FallbackExtractor
from app.services.parsing.models import EntryPointHint, ParsedFile, SymbolInfo

logger = structlog.get_logger(__name__)


class JavaExtractor(BaseExtractor):
    def __init__(self) -> None:
        try:
            self.parser = tslp.get_parser("java")
        except Exception as e:
            logger.warning("java_parser_init_failed", error=str(e))
            self.parser = None

    def extract(self, source: str, path: str = "") -> ParsedFile:
        if not self.parser:
            try:
                self.parser = tslp.get_parser("java")
            except Exception:
                self.parser = None
        if not self.parser:
            return FallbackExtractor().extract(source, path)

        try:
            source_bytes = source.encode("utf-8")
            tree = self.parser.parse(source_bytes)
            root = tree.root_node
        except Exception as e:
            logger.warning("java_parse_failed", path=path, error=str(e))
            return FallbackExtractor().extract(source, path)

        symbols: list[SymbolInfo] = []
        imports: list[str] = []
        entry_point_hints: list[EntryPointHint] = []
        top_level_ranges: list[tuple[int, int]] = []
        package_name: str | None = None

        def get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

        def extract_leading_javadoc(node: tree_sitter.Node) -> str | None:
            prev = node.prev_named_sibling
            if prev and prev.type == "block_comment":
                raw = get_node_text(prev).strip()
                if raw.startswith("/**") and raw.endswith("*/"):
                    lines = raw[3:-2].strip().splitlines()
                    clean = [line.strip().lstrip("*").strip() for line in lines]
                    return "\n".join(clean).strip()
                return raw
            return None

        def process_class_or_interface(
            node: tree_sitter.Node,
        ) -> tuple[SymbolInfo, list[SymbolInfo]]:
            name_node = node.child_by_field_name("name")
            name = get_node_text(name_node) if name_node else "AnonymousType"

            kind_map = {
                "class_declaration": "class",
                "interface_declaration": "interface",
                "enum_declaration": "enum",
                "record_declaration": "struct",
            }
            kind = kind_map.get(node.type, "class")

            # Extract modifiers and annotations
            annotations: list[str] = []
            modifiers_node = None
            for child in node.children:
                if child.type == "modifiers":
                    modifiers_node = child
                    break

            if modifiers_node:
                for m in modifiers_node.children:
                    if m.type in ("annotation", "marker_annotation"):
                        ann_text = get_node_text(m)
                        annotations.append(ann_text)
                        if any(
                            r in ann_text
                            for r in [
                                "RestController",
                                "Controller",
                                "SpringBootApplication",
                                "Endpoint",
                            ]
                        ):
                            entry_point_hints.append(
                                EntryPointHint(
                                    reason=f"Spring Framework entry component: {ann_text}",
                                    line=node.start_point[0] + 1,
                                    symbol=name,
                                )
                            )

            doc = extract_leading_javadoc(node)
            start_l = node.start_point[0] + 1
            end_l = node.end_point[0] + 1

            ann_prefix = " ".join(annotations) + " " if annotations else ""
            signature = f"{ann_prefix}{kind} {name}"

            type_sym = SymbolInfo(
                name=name,
                qualified_name=name,
                kind=kind,
                signature=signature,
                start_line=start_l,
                end_line=end_l,
                language="java",
                docstring=doc,
                parent=None,
                exported=True,
            )

            methods: list[SymbolInfo] = []
            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    if child.type in ("method_declaration", "constructor_declaration"):
                        m_name_node = child.child_by_field_name("name")
                        m_name = get_node_text(m_name_node) if m_name_node else "method"

                        m_params = child.child_by_field_name("parameters")
                        m_sig_params = get_node_text(m_params) if m_params else "()"

                        m_type = child.child_by_field_name("type")
                        m_ret = f"{get_node_text(m_type)} " if m_type else ""

                        # Check main entry point: public static void main
                        m_mods = None
                        for sub in child.children:
                            if sub.type == "modifiers":
                                m_mods = get_node_text(sub)
                                break

                        if (
                            m_mods
                            and "public" in m_mods
                            and "static" in m_mods
                            and m_name == "main"
                        ):
                            entry_point_hints.append(
                                EntryPointHint(
                                    reason="Java Entry point: public static void main",
                                    line=child.start_point[0] + 1,
                                    symbol=f"{name}.main",
                                )
                            )

                        # Check route mapping annotations on method: @GetMapping, @PostMapping, etc.
                        if m_mods and any(
                            r in m_mods
                            for r in [
                                "GetMapping",
                                "PostMapping",
                                "PutMapping",
                                "DeleteMapping",
                                "RequestMapping",
                            ]
                        ):
                            entry_point_hints.append(
                                EntryPointHint(
                                    reason=f"Spring route handler: {m_name}",
                                    line=child.start_point[0] + 1,
                                    symbol=f"{name}.{m_name}",
                                )
                            )

                        m_sig = f"{m_ret}{m_name}{m_sig_params}"
                        m_doc = extract_leading_javadoc(child)

                        methods.append(
                            SymbolInfo(
                                name=m_name,
                                qualified_name=f"{name}.{m_name}",
                                kind="method",
                                signature=m_sig,
                                start_line=child.start_point[0] + 1,
                                end_line=child.end_point[0] + 1,
                                language="java",
                                docstring=m_doc,
                                parent=name,
                                exported=True,
                            )
                        )

            return type_sym, methods

        for child in root.children:
            start_l = child.start_point[0] + 1
            end_l = child.end_point[0] + 1

            if child.type == "package_declaration":
                # package com.example.app;
                for sub in child.children:
                    if sub.type in ("scoped_identifier", "identifier"):
                        package_name = get_node_text(sub)
                top_level_ranges.append((start_l, end_l))

            elif child.type == "import_declaration":
                # import com.example.Foo;
                for sub in child.children:
                    if sub.type in ("scoped_identifier", "identifier"):
                        imports.append(get_node_text(sub))
                top_level_ranges.append((start_l, end_l))

            elif child.type in (
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
                "record_declaration",
            ):
                cls_sym, methods = process_class_or_interface(child)
                symbols.append(cls_sym)
                symbols.extend(methods)
                top_level_ranges.append((start_l, end_l))

        card = self.build_file_card(
            path=path,
            language="java",
            module_docstring=f"Package: {package_name}" if package_name else None,
            imports=imports,
            symbols=symbols,
        )

        return ParsedFile(
            path=path,
            language="java",
            symbols=symbols,
            imports=sorted(set(imports)),
            module_docstring=f"package {package_name};" if package_name else None,
            top_level_ranges=top_level_ranges,
            entry_point_hints=entry_point_hints,
            card=card,
        )
