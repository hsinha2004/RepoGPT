from __future__ import annotations

import posixpath
from typing import Any

import networkx as nx  # type: ignore[import-untyped]


class GraphAnalyzer:
    """NetworkX-based dependency graph analysis, metrics computation, and filtering (§8.8)."""

    def __init__(self, edges: list[dict[str, Any]], all_files: list[str]) -> None:
        self.raw_edges = edges
        self.all_files = set(all_files)

        # Build full directed graph of imports (internal + external)
        self.full_graph = nx.DiGraph()
        # Add all project files as nodes (so orphans exist)
        for f in self.all_files:
            self.full_graph.add_node(f, is_external=False)

        for e in edges:
            src = e["source"]
            tgt = e["target"]
            edge_type = e.get("type", "imports")
            heuristic = e.get("heuristic", False)
            symbol = e.get("symbol")

            if not self.full_graph.has_node(src):
                self.full_graph.add_node(src, is_external=src.startswith("ext:"))
            if not self.full_graph.has_node(tgt):
                self.full_graph.add_node(tgt, is_external=tgt.startswith("ext:"))

            self.full_graph.add_edge(
                src,
                tgt,
                type=edge_type,
                heuristic=heuristic,
                symbol=symbol,
            )

        # Internal file-only import graph for PageRank and cycle detection
        self.internal_import_graph = nx.DiGraph()
        for f in self.all_files:
            self.internal_import_graph.add_node(f)

        for e in edges:
            if e.get("type", "imports") == "imports" and not e.get("heuristic", False):
                src = e["source"]
                tgt = e["target"]
                if not tgt.startswith("ext:") and src in self.all_files and tgt in self.all_files:
                    self.internal_import_graph.add_edge(src, tgt)

    def compute_file_metrics(self) -> dict[str, dict[str, Any]]:
        """Calculates PageRank, fan-in, fan-out, cycles, and orphan status per internal file.

        Returns:
            Mapping of file_path -> {
                "pagerank": float,
                "fan_in": int,
                "fan_out": int,
                "in_cycle": bool,
                "is_orphan": bool,
            }
        """
        # PageRank with damping 0.85
        try:
            if len(self.internal_import_graph) > 0:
                pagerank_scores = nx.pagerank(self.internal_import_graph, alpha=0.85)
            else:
                pagerank_scores = {}
        except Exception:
            pagerank_scores = {f: 1.0 / max(len(self.all_files), 1) for f in self.all_files}

        # Cycles detection (bounded search, max 50 simple cycles)
        cycles = self.detect_cycles(max_cycles=50)
        cycle_nodes: set[str] = set()
        for c in cycles:
            cycle_nodes.update(c)

        metrics: dict[str, dict[str, Any]] = {}
        for f in self.all_files:
            in_deg = (
                self.internal_import_graph.in_degree(f)
                if self.internal_import_graph.has_node(f)
                else 0
            )
            out_deg = (
                self.internal_import_graph.out_degree(f)
                if self.internal_import_graph.has_node(f)
                else 0
            )
            pr = round(float(pagerank_scores.get(f, 0.0)), 6)

            metrics[f] = {
                "pagerank": pr,
                "fan_in": in_deg,
                "fan_out": out_deg,
                "in_cycle": f in cycle_nodes,
                "is_orphan": (in_deg == 0 and out_deg == 0),
            }

        return metrics

    def detect_cycles(self, max_cycles: int = 50) -> list[list[str]]:
        """Finds up to max_cycles simple cycles in the internal import graph."""
        cycles: list[list[str]] = []
        try:
            # simple_cycles generates cycles; limit to max_cycles and length <= 12
            for c in nx.simple_cycles(self.internal_import_graph):
                if len(c) <= 12:
                    cycles.append(c)
                if len(cycles) >= max_cycles:
                    break
        except Exception:
            pass
        return cycles

    def get_orphan_files(self) -> list[str]:
        """Returns files with degree 0 (no imports and not imported)."""
        return sorted(
            [
                f
                for f in self.all_files
                if self.internal_import_graph.has_node(f)
                and self.internal_import_graph.degree(f) == 0
            ]
        )

    def get_components(self) -> list[list[str]]:
        """Returns weakly connected components of the internal import graph."""
        try:
            comps = list(nx.weakly_connected_components(self.internal_import_graph))
            return [sorted(c) for c in comps]
        except Exception:
            return []

    def get_graph_view(
        self,
        level: str = "file",
        depth: int | None = None,
        focus: str | None = None,
        hops: int = 1,
        include_external: bool = False,
        include_calls: bool = True,
    ) -> dict[str, Any]:
        """Builds a filtered or aggregated graph view for UI rendering (§8.8, §12).

        Args:
            level: 'file' or 'directory'.
            depth: Directory depth for aggregation if level=='directory' (default 1).
            focus: Path of focal file/directory for ego-graph view.
            hops: Max hops around focus node.
            include_external: Whether to include ext:<pkg> nodes and edges.
            include_calls: Whether to include heuristic call edges.

        Returns:
            Dict with:
                - nodes: list[dict]
                - edges: list[dict]
                - cycles: list[list[str]]
                - metrics: summary dict
                - level: str
        """
        if level == "directory":
            return self._aggregate_directory_view(
                depth=depth or 1,
                focus=focus,
                hops=hops,
                include_external=include_external,
            )

        # File-level graph
        G = self.full_graph

        # Filter edges by external and calls
        candidate_edges = []
        for u, v, data in G.edges(data=True):
            is_ext = u.startswith("ext:") or v.startswith("ext:")
            if is_ext and not include_external:
                continue
            is_call = data.get("type") == "calls"
            if is_call and not include_calls:
                continue
            candidate_edges.append((u, v, data))

        # Build active subgraph
        active_G = nx.DiGraph()
        for u, v, data in candidate_edges:
            active_G.add_edge(u, v, **data)

        # Ensure internal non-orphan files are added
        for f in self.all_files:
            if not active_G.has_node(f):
                active_G.add_node(f, is_external=False)

        # Focus / Ego graph filtering
        if focus and active_G.has_node(focus):
            try:
                ego_nodes = set(
                    nx.single_source_shortest_path_length(
                        active_G.to_undirected(), focus, cutoff=hops
                    ).keys()
                )
                active_G = active_G.subgraph(ego_nodes).copy()
            except Exception:
                pass

        # Cap nodes at 400 (if larger, automatically fallback to directory level)
        if len(active_G.nodes) > 400:
            return self._aggregate_directory_view(
                depth=depth or 1,
                focus=focus,
                hops=hops,
                include_external=include_external,
            )

        # Prepare Nodes and Edges
        file_metrics = self.compute_file_metrics()
        cycles = self.detect_cycles(max_cycles=30)
        cycle_node_set = {n for c in cycles for n in c}

        nodes_list: list[dict[str, Any]] = []
        for node in active_G.nodes():
            is_ext = node.startswith("ext:")
            m = file_metrics.get(node, {})

            # Top-level directory for color categorization
            top_dir = self._get_top_directory(node)

            nodes_list.append(
                {
                    "id": node,
                    "label": posixpath.basename(node) if not is_ext else node[4:],
                    "full_path": node,
                    "is_external": is_ext,
                    "top_directory": top_dir,
                    "fan_in": m.get("fan_in", 0),
                    "fan_out": m.get("fan_out", 0),
                    "pagerank": m.get("pagerank", 0.0),
                    "in_cycle": node in cycle_node_set,
                    "is_orphan": m.get("is_orphan", False),
                }
            )

        edges_list: list[dict[str, Any]] = []
        for i, (u, v, data) in enumerate(active_G.edges(data=True)):
            edges_list.append(
                {
                    "id": f"e_{i}_{u}_{v}",
                    "source": u,
                    "target": v,
                    "type": data.get("type", "imports"),
                    "heuristic": data.get("heuristic", False),
                    "symbol": data.get("symbol"),
                    "weight": data.get("weight", 1),
                }
            )

        return {
            "level": "file",
            "nodes": nodes_list,
            "edges": edges_list,
            "cycles": cycles,
            "total_nodes": len(nodes_list),
            "total_edges": len(edges_list),
            "orphan_count": len(self.get_orphan_files()),
        }

    def _aggregate_directory_view(
        self,
        depth: int,
        focus: str | None,
        hops: int,
        include_external: bool,
    ) -> dict[str, Any]:
        """Aggregates files into directory-level nodes with summed edge weights (§8.8)."""
        dir_graph = nx.DiGraph()

        # Map each file to its directory up to specified depth
        def get_dir_node(path: str) -> str:
            if path.startswith("ext:"):
                return path
            parts = [p for p in path.split("/") if p]
            if len(parts) <= 1:
                return "<root>"
            dir_parts = parts[:-1]
            return "/".join(dir_parts[:depth])

        dir_file_counts: dict[str, int] = {}
        for f in self.all_files:
            d = get_dir_node(f)
            dir_file_counts[d] = dir_file_counts.get(d, 0) + 1
            if not dir_graph.has_node(d):
                dir_graph.add_node(d, is_external=False, file_count=0)

        for d, count in dir_file_counts.items():
            dir_graph.nodes[d]["file_count"] = count

        # Aggregate edges
        edge_weights: dict[tuple[str, str], int] = {}
        for e in self.raw_edges:
            src = e["source"]
            tgt = e["target"]
            if tgt.startswith("ext:") and not include_external:
                continue

            src_d = get_dir_node(src)
            tgt_d = get_dir_node(tgt)

            if src_d == tgt_d:
                continue  # Ignore intra-directory loops

            key = (src_d, tgt_d)
            edge_weights[key] = edge_weights.get(key, 0) + 1

        for (u, v), weight in edge_weights.items():
            if not dir_graph.has_node(u):
                dir_graph.add_node(u, is_external=u.startswith("ext:"), file_count=0)
            if not dir_graph.has_node(v):
                dir_graph.add_node(v, is_external=v.startswith("ext:"), file_count=0)
            dir_graph.add_edge(u, v, weight=weight)

        # Focus filter if provided
        if focus and dir_graph.has_node(focus):
            try:
                ego_nodes = set(
                    nx.single_source_shortest_path_length(
                        dir_graph.to_undirected(), focus, cutoff=hops
                    ).keys()
                )
                dir_graph = dir_graph.subgraph(ego_nodes).copy()
            except Exception:
                pass

        # Compute directory cycles
        cycles: list[list[str]] = []
        try:
            for c in nx.simple_cycles(dir_graph):
                cycles.append(c)
                if len(cycles) >= 20:
                    break
        except Exception:
            pass

        cycle_nodes = {n for c in cycles for n in c}

        nodes_list: list[dict[str, Any]] = []
        for node, data in dir_graph.nodes(data=True):
            is_ext = node.startswith("ext:")
            in_deg = dir_graph.in_degree(node)
            out_deg = dir_graph.out_degree(node)

            nodes_list.append(
                {
                    "id": node,
                    "label": node[4:] if is_ext else node,
                    "full_path": node,
                    "is_external": is_ext,
                    "top_directory": node.split("/")[0] if not is_ext else "external",
                    "fan_in": in_deg,
                    "fan_out": out_deg,
                    "pagerank": round(1.0 / max(len(dir_graph), 1), 4),
                    "in_cycle": node in cycle_nodes,
                    "is_orphan": (in_deg == 0 and out_deg == 0),
                    "file_count": data.get("file_count", 0),
                }
            )

        edges_list: list[dict[str, Any]] = []
        for i, (u, v, data) in enumerate(dir_graph.edges(data=True)):
            edges_list.append(
                {
                    "id": f"dir_e_{i}_{u}_{v}",
                    "source": u,
                    "target": v,
                    "type": "imports",
                    "heuristic": False,
                    "symbol": None,
                    "weight": data.get("weight", 1),
                }
            )

        return {
            "level": "directory",
            "depth": depth,
            "nodes": nodes_list,
            "edges": edges_list,
            "cycles": cycles,
            "total_nodes": len(nodes_list),
            "total_edges": len(edges_list),
            "orphan_count": len([n for n in nodes_list if n["is_orphan"]]),
        }

    def _get_top_directory(self, path: str) -> str:
        """Extracts top-level directory name for color categorization."""
        if path.startswith("ext:"):
            return "external"
        parts = [p for p in path.split("/") if p]
        if len(parts) > 1:
            return parts[0]
        return "root"
