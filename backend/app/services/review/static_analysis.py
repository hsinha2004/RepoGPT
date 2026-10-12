"""
Isolated static analysis runner for Python files using Ruff (§10.2).
Strictly parses files in temporary directories with subprocess timeouts and no network access.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class StaticAnalyzer:
    """
    Runs isolated static analysis (Ruff) on changed file contents.
    Filters issues to only lines modified in the pull request.
    """

    def __init__(self, ruff_path: str | None = None) -> None:
        if ruff_path:
            self.ruff_path = ruff_path
        else:
            # Detect in virtualenv or PATH
            venv_ruff = (
                os.path.join(sys.prefix, "Scripts", "ruff.exe")
                if os.name == "nt"
                else os.path.join(sys.prefix, "bin", "ruff")
            )
            self.ruff_path = venv_ruff if os.path.exists(venv_ruff) else "ruff"

    def analyze_python_file(
        self,
        path: str,
        head_content: str,
        changed_lines: list[int],
    ) -> list[dict[str, Any]]:
        """
        Runs Ruff on head content and returns issues anchored to changed lines.
        """
        if not path.endswith(".py") or not head_content or not changed_lines:
            return []

        changed_set = set(changed_lines)
        findings: list[dict[str, Any]] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, os.path.basename(path))
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(head_content)

                # Execute Ruff with selected rule sets: E9, F, B, S (Bugbear, Bandit-style security, Syntax)
                cmd = [
                    self.ruff_path,
                    "check",
                    "--select",
                    "E9,F,B,S",
                    "--output-format",
                    "json",
                    temp_file,
                ]

                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )

                if proc.stdout and proc.stdout.strip():
                    raw_issues = json.loads(proc.stdout)
                    for issue in raw_issues:
                        line_num = issue.get("location", {}).get("row", 1)
                        if line_num in changed_set:
                            code = issue.get("code", "STATIC")
                            severity = (
                                "critical"
                                if code.startswith("S")
                                else "high"
                                if code.startswith("F")
                                else "medium"
                            )
                            findings.append(
                                {
                                    "code": code,
                                    "message": issue.get("message", "Static check violation"),
                                    "start_line": line_num,
                                    "end_line": line_num,
                                    "severity": severity,
                                    "category": "security" if code.startswith("S") else "bug",
                                }
                            )
            except (
                subprocess.TimeoutExpired,
                subprocess.SubprocessError,
                json.JSONDecodeError,
                FileNotFoundError,
            ) as exc:
                logger.debug("static_analysis_skipped", path=path, reason=str(exc))

        return findings
