"""
Go AST Extractor using tree-sitter (§8.4).
Extracts package, imports, functions, receiver methods (Type.Method),
structs, interfaces, and package main + func main entry points.
"""

import tree_sitter
import tree_sitter_language_pack as tslp

from app.services.parsing.extractors.base import BaseExtractor
from app.services.parsing.models import EntryPointHint, ParsedFile, SymbolInfo


class GoExtractor(BaseExtractor):
    def __init__(self) -> None:
        self.parser = tslp.get_parser("go")

    def extract(self, source: str, path: str = "") -> ParsedFile:
        source_bytes = source.encode("utf-8")
        tree = self.parser.parse(source_bytes)
        root = tree.root_node

        symbols: list[SymbolInfo] = []
        imports: list[str] = []
        entry_point_hints: list[EntryPointHint] = []
        top_level_ranges: list[tuple[int, int]] = []
        package_name: str | None = None

        def get_node_text(node: tree_sitter.Node) -> str:
            return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

        def extract_leading_comment(node: tree_sitter.Node) -> str | None:
            prev = node.prev_named_sibling
            if prev and prev.type == "comment":
                raw = get_node_text(prev).strip()
                return raw.lstrip("/").strip()
            return None

        for child in root.children:
            start_l = child.start_point[0] + 1
            end_l = child.end_point[0] + 1

            if child.type == "package_clause":
                for sub in child.children:
                    if sub.type == "package_identifier":
                        package_name = get_node_text(sub)
                top_level_ranges.append((start_l, end_l))

            elif child.type == "import_declaration":
                # import "fmt" or import ( "os" "path" )
                for spec in child.children:
                    if spec.type == "import_spec":
                        path_n = spec.child_by_field_name("path")
                        if path_n:
                            imports.append(get_node_text(path_n).strip('"'))
                    elif spec.type == "import_spec_list":
                        for sub_spec in spec.children:
                            if sub_spec.type == "import_spec":
                                path_n = sub_spec.child_by_field_name("path")
                                if path_n:
                                    imports.append(get_node_text(path_n).strip('"'))
                top_level_ranges.append((start_l, end_l))

            elif child.type == "function_declaration":
                name_n = child.child_by_field_name("name")
                name = get_node_text(name_n) if name_n else "anonymous"

                params_n = child.child_by_field_name("parameters")
                params = get_node_text(params_n) if params_n else "()"

                res_n = child.child_by_field_name("result")
                res = f" {get_node_text(res_n)}" if res_n else ""

                signature = f"func {name}{params}{res}"
                doc = extract_leading_comment(child)

                if package_name == "main" and name == "main":
                    entry_point_hints.append(
                        EntryPointHint(
                            reason="Go main entry point: package main; func main()",
                            line=start_l,
                            symbol="main",
                        )
                    )

                symbols.append(
                    SymbolInfo(
                        name=name,
                        qualified_name=name,
                        kind="function",
                        signature=signature,
                        start_line=start_l,
                        end_line=end_l,
                        language="go",
                        docstring=doc,
                        parent=None,
                        exported=name[0].isupper() if name else False,
                    )
                )
                top_level_ranges.append((start_l, end_l))

            elif child.type == "method_declaration":
                # Receiver method: func (r *Type) Method(...) ...
                rec_n = child.child_by_field_name("receiver")
                rec_text = get_node_text(rec_n) if rec_n else "()"

                # Extract receiver type name
                rec_type = "Receiver"
                if rec_n:
                    for sub in rec_n.children:
                        if sub.type == "parameter_declaration":
                            t_node = sub.child_by_field_name("type")
                            if t_node:
                                rec_type = get_node_text(t_node).lstrip("*").strip()

                name_n = child.child_by_field_name("name")
                name = get_node_text(name_n) if name_n else "method"

                params_n = child.child_by_field_name("parameters")
                params = get_node_text(params_n) if params_n else "()"

                res_n = child.child_by_field_name("result")
                res = f" {get_node_text(res_n)}" if res_n else ""

                signature = f"func {rec_text} {name}{params}{res}"
                doc = extract_leading_comment(child)
                qualified_name = f"{rec_type}.{name}"

                symbols.append(
                    SymbolInfo(
                        name=name,
                        qualified_name=qualified_name,
                        kind="method",
                        signature=signature,
                        start_line=start_l,
                        end_line=end_l,
                        language="go",
                        docstring=doc,
                        parent=rec_type,
                        exported=name[0].isupper() if name else False,
                    )
                )
                top_level_ranges.append((start_l, end_l))

            elif child.type == "type_declaration":
                for spec in child.children:
                    if spec.type == "type_spec":
                        name_n = spec.child_by_field_name("name")
                        name = get_node_text(name_n) if name_n else "Type"
                        type_n = spec.child_by_field_name("type")
                        t_type = type_n.type if type_n else ""

                        kind = "type"
                        if t_type == "struct_type":
                            kind = "struct"
                        elif t_type == "interface_type":
                            kind = "interface"

                        signature = f"type {name} {kind}"
                        doc = extract_leading_comment(child)

                        symbols.append(
                            SymbolInfo(
                                name=name,
                                qualified_name=name,
                                kind=kind,
                                signature=signature,
                                start_line=start_l,
                                end_line=end_l,
                                language="go",
                                docstring=doc,
                                parent=None,
                                exported=name[0].isupper() if name else False,
                            )
                        )
                top_level_ranges.append((start_l, end_l))

        card = self.build_file_card(
            path=path,
            language="go",
            module_docstring=f"package {package_name}" if package_name else None,
            imports=imports,
            symbols=symbols,
        )

        return ParsedFile(
            path=path,
            language="go",
            symbols=symbols,
            imports=sorted(set(imports)),
            module_docstring=f"package {package_name}" if package_name else None,
            top_level_ranges=top_level_ranges,
            entry_point_hints=entry_point_hints,
            card=card,
        )
