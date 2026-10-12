from __future__ import annotations

import re
from typing import Any

from app.services.graph.resolvers import get_import_resolver


class GraphBuilder:
    """Builds file-level and external dependency edges and heuristic call edges (§8.8)."""

    def build_edges(
        self,
        files: list[dict[str, Any]],
        symbols_by_file: dict[str, list[dict[str, Any]]] | None = None,
        go_module: str = "",
    ) -> list[dict[str, Any]]:
        """Constructs all import and heuristic call edges across project files.

        Args:
            files: List of file documents/dicts containing path, language, imports, content/text.
            symbols_by_file: Mapping of file_path -> list of symbols defined in that file.
            go_module: Optional go.mod module name for Go package resolution.

        Returns:
            List of edge dictionaries:
                - source: str (file path)
                - target: str (file path or ext:<pkg>)
                - type: 'imports' | 'calls'
                - heuristic: bool
                - symbol: str | None
        """
        all_project_files = {f.get("path", "") for f in files if f.get("path")}
        symbols_map = symbols_by_file or {}

        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str, str | None]] = set()

        # Map each file to the internal files it imports: source -> set[target_file]
        imports_map: dict[str, set[str]] = {f: set() for f in all_project_files}

        # 1. Resolve Import Edges
        for file_doc in files:
            source_path = file_doc.get("path", "")
            if not source_path:
                continue

            lang = file_doc.get("language", "")
            resolver = get_import_resolver(lang)
            raw_imports = file_doc.get("imports", [])

            for raw in raw_imports:
                import_spec = (
                    raw if isinstance(raw, str) else raw.get("module") or raw.get("name") or ""
                )
                if not import_spec:
                    continue

                if resolver:
                    resolved_target = resolver.resolve(
                        source_path=source_path,
                        raw_import=import_spec,
                        all_project_files=all_project_files,
                        go_module=go_module,
                    )
                else:
                    resolved_target = f"ext:{import_spec}"

                edge_key = (source_path, resolved_target, "imports", None)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append(
                        {
                            "source": source_path,
                            "target": resolved_target,
                            "type": "imports",
                            "heuristic": False,
                            "symbol": None,
                            "raw": import_spec,
                        }
                    )

                # If target is an internal project file, record it in imports_map
                if not resolved_target.startswith("ext:") and resolved_target in all_project_files:
                    imports_map[source_path].add(resolved_target)

        # 2. Heuristic Call Edges (§8.8)
        # For tier-1 languages, check if source file text references symbol names defined in imported files
        for file_doc in files:
            source_path = file_doc.get("path", "")
            if not source_path:
                continue

            imported_files = imports_map.get(source_path, set())
            if not imported_files:
                continue

            content = file_doc.get("content") or file_doc.get("text", "")
            if not content:
                continue

            # Tokenize source content identifiers
            tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", content))

            for imp_file in imported_files:
                target_symbols = symbols_map.get(imp_file, [])
                for sym in target_symbols:
                    sym_name = sym.get("name", "")
                    sym_kind = sym.get("kind", "")
                    # Check for functions, methods, and classes
                    if sym_name and sym_kind in (
                        "function",
                        "method",
                        "class",
                        "struct",
                        "interface",
                    ):
                        if sym_name in tokens:
                            edge_key = (source_path, imp_file, "calls", sym_name)
                            if edge_key not in seen_edges:
                                seen_edges.add(edge_key)
                                edges.append(
                                    {
                                        "source": source_path,
                                        "target": imp_file,
                                        "type": "calls",
                                        "heuristic": True,
                                        "symbol": sym_name,
                                        "raw": None,
                                    }
                                )

        return edges
