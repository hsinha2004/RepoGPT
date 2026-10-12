from __future__ import annotations

from typing import Any


class ReadingOrderGenerator:
    """Generates a structured, deterministic 10-15 step codebase reading order (§8.8)."""

    def generate(
        self,
        all_files: list[str],
        entry_points: list[dict[str, Any]],
        file_metrics: dict[str, dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Produces ordered reading list with categories and rationale.

        Steps order:
            1. Documentation & Architecture (README.md, docs/*.md)
            2. Application Entry Points
            3. Top PageRank Modules (Core abstractions)
            4. Breadth-first along imports from entry points
            5. Key Configuration (docker, yaml, settings)
        """
        items: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        def add_item(path: str, category: str, reason: str) -> None:
            if path in all_files and path not in seen_paths and len(items) < 15:
                seen_paths.add(path)
                items.append(
                    {
                        "step": len(items) + 1,
                        "path": path,
                        "category": category,
                        "reason": reason,
                    }
                )

        # 1. Documentation & Architecture
        doc_candidates = [
            f
            for f in all_files
            if f.lower().startswith("readme")
            or "docs/architecture" in f.lower()
            or "docs/spec" in f.lower()
        ]
        doc_candidates.sort(key=lambda x: (0 if "readme" in x.lower() else 1, x))
        for d in doc_candidates[:3]:
            add_item(
                d,
                "documentation",
                "High-level repository overview, project goals, and system architecture",
            )

        # 2. Application Entry Points
        for ep in entry_points[:4]:
            ep_path = ep["path"]
            add_item(
                ep_path,
                "entry_point",
                f"Application lifecycle bootstrap: {ep.get('description', 'Entry point')}",
            )

        # 3. Top PageRank Modules (Highest incoming dependency centrality)
        # Exclude already seen and non-code files
        ranked_files = sorted(
            [f for f in all_files if f in file_metrics],
            key=lambda f: file_metrics[f].get("pagerank", 0.0),
            reverse=True,
        )
        for rf in ranked_files:
            pr = file_metrics[rf].get("pagerank", 0.0)
            if pr > 0:
                add_item(
                    rf, "core_module", f"Central architectural dependency (PageRank score {pr:.4f})"
                )
            if len(items) >= 9:
                break

        # 4. Breadth-First search along imports from entry points
        # Build adjacency list: src -> list[targets]
        adj: dict[str, list[str]] = {}
        for e in edges:
            src = e.get("source", "")
            tgt = e.get("target", "")
            if src and tgt and not tgt.startswith("ext:"):
                adj.setdefault(src, []).append(tgt)

        queue = [ep["path"] for ep in entry_points if ep["path"] in all_files]
        while queue and len(items) < 12:
            curr = queue.pop(0)
            for neighbor in adj.get(curr, []):
                if neighbor in all_files and neighbor not in seen_paths:
                    add_item(
                        neighbor,
                        "flow_path",
                        f"Direct dependency in the primary call flow from {curr}",
                    )
                    queue.append(neighbor)
                if len(items) >= 12:
                    break

        # 5. Key Configuration & Infrastructure
        config_candidates = [
            f
            for f in all_files
            if f.endswith(
                (
                    "docker-compose.yml",
                    "docker-compose.yaml",
                    "Dockerfile",
                    "settings.yaml",
                    "config.py",
                    ".env.example",
                )
            )
        ]
        config_candidates.sort()
        for cfg in config_candidates:
            add_item(
                cfg,
                "configuration",
                "Runtime configuration, deployment setup, and environment specifications",
            )
            if len(items) >= 15:
                break

        # If fewer than 10 items, pad with remaining top files
        if len(items) < 10:
            for f in sorted(all_files):
                if f not in seen_paths and not f.startswith("."):
                    add_item(f, "general", "Source component in the project structure")
                if len(items) >= 10:
                    break

        return items
