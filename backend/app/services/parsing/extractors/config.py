"""
Configuration & Manifest Extractor (§8.4).
Parses JSON, YAML, TOML, Dockerfile, Makefile and extracts top-level sections,
dependencies, and entry point hints.
"""

import json
import re

import yaml

from app.services.parsing.extractors.base import BaseExtractor
from app.services.parsing.models import EntryPointHint, ParsedFile, SymbolInfo


class ConfigExtractor(BaseExtractor):
    def extract(self, source: str, path: str = "") -> ParsedFile:
        lines = source.splitlines()
        symbols: list[SymbolInfo] = []
        entry_points: list[EntryPointHint] = []
        imports: list[str] = []
        filename = path.split("/")[-1].lower()

        # Handle Dockerfile
        if "dockerfile" in filename:
            for idx, line in enumerate(lines, 1):
                clean = line.strip()
                if clean.startswith("ENTRYPOINT") or clean.startswith("CMD"):
                    entry_points.append(
                        EntryPointHint(
                            reason=f"Docker container command: {clean[:40]}",
                            line=idx,
                            symbol="container_entrypoint",
                        )
                    )
                elif clean.startswith("FROM"):
                    parts = clean.split()
                    if len(parts) > 1:
                        imports.append(parts[1])
                elif re.match(r"^[A-Z]+\s+", clean):
                    instruction = clean.split()[0]
                    symbols.append(
                        SymbolInfo(
                            name=instruction,
                            qualified_name=f"{path}:{instruction}:{idx}",
                            kind="const",
                            signature=clean[:80],
                            start_line=idx,
                            end_line=idx,
                            language="dockerfile",
                        )
                    )

        # Handle Makefile
        elif filename == "makefile":
            target_re = re.compile(r"^([a-zA-Z0-9_\-\.]+)\s*:")
            for idx, line in enumerate(lines, 1):
                m = target_re.match(line)
                if m:
                    target = m.group(1)
                    if target in ("run", "start", "dev", "serve"):
                        entry_points.append(
                            EntryPointHint(
                                reason=f"Makefile run target: make {target}",
                                line=idx,
                                symbol=target,
                            )
                        )
                    symbols.append(
                        SymbolInfo(
                            name=target,
                            qualified_name=f"make {target}",
                            kind="function",
                            signature=f"{target}:",
                            start_line=idx,
                            end_line=idx,
                            language="makefile",
                        )
                    )

        # Handle JSON (e.g. package.json)
        elif path.endswith(".json"):
            try:
                data = json.loads(source)
                if isinstance(data, dict):
                    # Check package.json entrypoints
                    if "main" in data:
                        entry_points.append(
                            EntryPointHint(
                                reason=f"package.json main: {data['main']}",
                                line=1,
                                symbol="main",
                            )
                        )
                    if "scripts" in data and isinstance(data["scripts"], dict):
                        if "start" in data["scripts"]:
                            entry_points.append(
                                EntryPointHint(
                                    reason=f"npm start: {data['scripts']['start']}",
                                    line=1,
                                    symbol="npm_start",
                                )
                            )
                    # Extract top-level keys
                    for k in data.keys():
                        symbols.append(
                            SymbolInfo(
                                name=str(k),
                                qualified_name=f"{path} > {k}",
                                kind="const",
                                signature=f"key: {k}",
                                start_line=1,
                                end_line=len(lines) if lines else 1,
                                language="json",
                            )
                        )
            except Exception:
                pass

        # Handle YAML (e.g. docker-compose.yml, workflows)
        elif path.endswith(".yml") or path.endswith(".yaml"):
            try:
                data = yaml.safe_load(source)
                if isinstance(data, dict):
                    for k in data.keys():
                        symbols.append(
                            SymbolInfo(
                                name=str(k),
                                qualified_name=f"{path} > {k}",
                                kind="const",
                                signature=f"section: {k}",
                                start_line=1,
                                end_line=len(lines) if lines else 1,
                                language="yaml",
                            )
                        )
            except Exception:
                pass

        card = self.build_file_card(
            path=path,
            language="config",
            module_docstring=f"Configuration file: {filename}",
            imports=imports,
            symbols=symbols,
        )

        return ParsedFile(
            path=path,
            language="config",
            symbols=symbols,
            imports=imports,
            module_docstring=f"Configuration file: {filename}",
            top_level_ranges=[(1, len(lines))] if lines else [],
            entry_point_hints=entry_points,
            card=card,
        )
