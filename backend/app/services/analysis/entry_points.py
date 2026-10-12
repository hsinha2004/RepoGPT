from __future__ import annotations

import json
import re
from typing import Any


class EntryPointDetector:
    """Detects application entry points across languages and framework conventions (§8.8)."""

    def detect(self, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Scans codebase files for runnable entry points.

        Returns list of entry points:
            [{"path": "backend/app/main.py", "kind": "app_factory", "description": "FastAPI application factory"}]
        """
        entry_points: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str]] = set()

        def add_entry(path: str, kind: str, description: str, line: int = 1) -> None:
            key = (path, kind)
            if key not in seen_keys:
                seen_keys.add(key)
                entry_points.append(
                    {
                        "path": path,
                        "kind": kind,
                        "description": description,
                        "line": line,
                    }
                )

        for file_doc in files:
            path = file_doc.get("path", "")
            if not path:
                continue

            content = file_doc.get("content") or file_doc.get("text", "")
            base = path.split("/")[-1]

            # 1. Python Entry Points
            if path.endswith(".py"):
                # __main__ block
                if '__name__ == "__main__"' in content or "__name__ == '__main__'" in content:
                    add_entry(path, "main_block", "Python __main__ execution entrypoint")

                # Framework app factories
                if "FastAPI(" in content:
                    add_entry(path, "app_factory", "FastAPI web application instantiation")
                elif "Flask(__name__)" in content or "Flask(" in content:
                    add_entry(path, "app_factory", "Flask web application instantiation")
                elif base == "manage.py" and "django" in content:
                    add_entry(path, "cli_entry", "Django management CLI")
                elif base in ("wsgi.py", "asgi.py"):
                    add_entry(path, "server_gateway", f"Python {base.upper()} gateway entrypoint")

            # 2. Go Entry Points
            elif path.endswith(".go"):
                if re.search(r"package\s+main\b", content) and re.search(
                    r"func\s+main\s*\(\s*\)", content
                ):
                    add_entry(path, "go_main", "Go main executable package and entry function")

            # 3. Java Entry Points
            elif path.endswith(".java"):
                if re.search(r"public\s+static\s+void\s+main\s*\(", content):
                    add_entry(
                        path, "java_main", "Java public static void main execution entrypoint"
                    )
                elif "@SpringBootApplication" in content:
                    add_entry(path, "spring_boot_app", "Spring Boot application entrypoint")

            # 4. JavaScript / TypeScript Entry Points
            elif path.endswith((".tsx", ".jsx", ".ts", ".js")):
                if base in ("main.tsx", "main.jsx", "index.tsx", "index.jsx") and (
                    "createRoot" in content or "ReactDOM" in content
                ):
                    add_entry(path, "ui_root", "React DOM application root mount")
                elif base in ("server.ts", "server.js", "app.ts", "app.js") and (
                    "express()" in content or "createServer" in content or "listen(" in content
                ):
                    add_entry(path, "server_entry", "Node.js HTTP server entrypoint")

            # 5. package.json scripts / main / bin
            elif base == "package.json":
                try:
                    data = json.loads(content)
                    if "bin" in data:
                        add_entry(path, "npm_bin", f"NPM executable binary ({data['bin']})")
                    if "scripts" in data and "start" in data["scripts"]:
                        add_entry(
                            path, "npm_start", f"NPM start script: '{data['scripts']['start']}'"
                        )
                    elif "scripts" in data and "dev" in data["scripts"]:
                        add_entry(path, "npm_dev", f"NPM dev script: '{data['scripts']['dev']}'")
                except Exception:
                    pass

            # 6. Dockerfile CMD / ENTRYPOINT
            elif "dockerfile" in base.lower():
                cmd_match = re.search(r"^\s*(CMD|ENTRYPOINT)\s+(.+)$", content, re.MULTILINE)
                if cmd_match:
                    add_entry(
                        path,
                        "container_entry",
                        f"Container {cmd_match.group(1)}: {cmd_match.group(2).strip()}",
                    )

        # Sort entry points deterministically
        return sorted(entry_points, key=lambda x: (x["kind"], x["path"]))
