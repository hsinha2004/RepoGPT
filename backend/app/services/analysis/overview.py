from __future__ import annotations

import json
from typing import Any

import structlog

from app.core.config import get_settings
from app.services.chat.citations import verify_and_clean_citations
from app.services.llm.base import ChatMessage, LLMProvider

logger = structlog.get_logger(__name__)


class OverviewService:
    """Generates structured onboarding overview and suggested questions (§8.9)."""

    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def generate_overview(
        self,
        repo_name: str,
        commit_sha: str,
        readme_text: str,
        tech_stack: list[dict[str, Any]],
        entry_points: list[dict[str, Any]],
        reading_order: list[dict[str, Any]],
        file_metrics: dict[str, dict[str, Any]],
        top_files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Produces repo onboarding overview with [S#] citations and suggested questions."""
        # 1. Prepare numbered sources from top files and docs
        sources_list: list[dict[str, Any]] = []
        source_id_counter = 1

        # Source 1: README if available
        if readme_text:
            s_id = f"S{source_id_counter}"
            source_id_counter += 1
            sources_list.append(
                {
                    "id": s_id,
                    "path": "README.md",
                    "start_line": 1,
                    "end_line": len(readme_text.splitlines()) or 1,
                    "symbol": None,
                    "snippet": readme_text[:600],
                }
            )

        # Top file cards
        for f in top_files[:14]:
            s_id = f"S{source_id_counter}"
            source_id_counter += 1
            sources_list.append(
                {
                    "id": s_id,
                    "path": f.get("path", ""),
                    "start_line": 1,
                    "end_line": f.get("loc", 50),
                    "symbol": f.get("symbol_name"),
                    "snippet": f.get("text", "")[:300] or f.get("summary", "")[:300],
                }
            )

        sources_context = {s["id"]: s for s in sources_list}

        # 2. Decide between LLM and deterministic heuristic generation
        if self.llm.name != "fake":
            try:
                overview_md, questions = await self._generate_with_llm(
                    repo_name=repo_name,
                    commit_sha=commit_sha,
                    readme_text=readme_text,
                    tech_stack=tech_stack,
                    entry_points=entry_points,
                    reading_order=reading_order,
                    file_metrics=file_metrics,
                    sources_list=sources_list,
                )
            except Exception as e:
                logger.warning("overview_llm_failed_falling_back_to_heuristic", error=str(e))
                overview_md, questions = self._generate_heuristic(
                    repo_name=repo_name,
                    tech_stack=tech_stack,
                    entry_points=entry_points,
                    reading_order=reading_order,
                    file_metrics=file_metrics,
                    sources_list=sources_list,
                    readme_text=readme_text,
                )
        else:
            overview_md, questions = self._generate_heuristic(
                repo_name=repo_name,
                tech_stack=tech_stack,
                entry_points=entry_points,
                reading_order=reading_order,
                file_metrics=file_metrics,
                sources_list=sources_list,
                readme_text=readme_text,
            )

        # 3. Clean citations against available sources
        clean_result = verify_and_clean_citations(overview_md, sources_context)

        return {
            "markdown": clean_result.cleaned_text,
            "suggested_questions": questions,
            "sources": sources_list,
            "tech_stack": tech_stack,
            "entry_points": entry_points,
            "reading_order": reading_order,
        }

    async def _generate_with_llm(
        self,
        repo_name: str,
        commit_sha: str,
        readme_text: str,
        tech_stack: list[dict[str, Any]],
        entry_points: list[dict[str, Any]],
        reading_order: list[dict[str, Any]],
        file_metrics: dict[str, dict[str, Any]],
        sources_list: list[dict[str, Any]],
    ) -> tuple[str, list[str]]:
        """Invokes LLM with strict prompt to produce onboarding overview (§8.9)."""
        prompt_sources = "\n".join(
            f'<source id="{s["id"]}" path="{s["path"]}">\n{s["snippet"]}\n</source>'
            for s in sources_list
        )

        tech_summary = ", ".join(t["name"] for t in tech_stack[:10])
        entry_summary = ", ".join(f"{e['path']} ({e['kind']})" for e in entry_points[:5])
        reading_summary = ", ".join(r["path"] for r in reading_order[:5])
        readme_snippet = readme_text[:500] if readme_text else ""

        system_msg = (
            "You are RepoGPT, generating an onboarding architectural overview of a repository for developers.\n"
            "Produce structured Markdown with the following exact sections:\n"
            "## What this project is\n"
            "## Architecture at a glance\n"
            "## Key modules\n"
            "## How a request flows\n"
            "## How to run\n"
            "## Where to start\n\n"
            "Rules:\n"
            "1. Support every claim with inline [S#] citations from <sources>.\n"
            "2. At the very end of your response, output a JSON block with 6-8 repo-specific suggested questions:\n"
            '```json\n{"suggested_questions": ["..."]}\n```'
        )

        user_msg = (
            f"<sources>\n{prompt_sources}\n</sources>\n\n"
            f"Repository: {repo_name} @ {commit_sha[:7]}\n"
            f"Detected Tech: {tech_summary}\n"
            f"Entry Points: {entry_summary}\n"
            f"Suggested Reading Order: {reading_summary}\n"
            f"README snippet: {readme_snippet}\n"
            "Generate the onboarding overview now."
        )

        res = await self.llm.complete(
            [
                ChatMessage(role="system", content=system_msg),
                ChatMessage(role="user", content=user_msg),
            ],
            model=get_settings().LLM_MODEL or "default",
            max_tokens=2000,
            temperature=0.2,
        )

        text = res.text
        # Extract suggested questions if present
        questions: list[str] = []
        if "```json" in text:
            parts = text.split("```json")
            text = parts[0].strip()
            json_block = parts[1].split("```")[0].strip()
            try:
                parsed = json.loads(json_block)
                questions = parsed.get("suggested_questions", [])
            except Exception:
                pass

        if not questions:
            questions = self._default_questions(entry_points, file_metrics)

        return text, questions

    def _generate_heuristic(
        self,
        repo_name: str,
        tech_stack: list[dict[str, Any]],
        entry_points: list[dict[str, Any]],
        reading_order: list[dict[str, Any]],
        file_metrics: dict[str, dict[str, Any]],
        sources_list: list[dict[str, Any]],
        readme_text: str,
    ) -> tuple[str, list[str]]:
        """Deterministic heuristic generator for offline mode and tests (§8.9)."""
        # Map paths to source IDs
        path_to_sid: dict[str, str] = {s["path"]: s["id"] for s in sources_list}
        readme_sid = path_to_sid.get("README.md", "S1")

        # Top PageRank modules
        top_ranked = sorted(
            [f for f, m in file_metrics.items() if m.get("pagerank", 0.0) > 0],
            key=lambda f: file_metrics[f].get("pagerank", 0.0),
            reverse=True,
        )[:6]

        tech_by_cat: dict[str, list[str]] = {}
        for t in tech_stack:
            tech_by_cat.setdefault(t["category"], []).append(t["name"])

        frameworks = ", ".join(tech_by_cat.get("framework", ["Custom"]))
        databases = ", ".join(tech_by_cat.get("database", ["File-system / In-memory"]))
        languages = ", ".join(tech_by_cat.get("language", []))

        # 1. What this project is
        first_readme_para = ""
        if readme_text:
            lines = [
                line.strip()
                for line in readme_text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if lines:
                first_readme_para = lines[0]

        what_it_is = (
            f"**{repo_name}** is a software system built using {languages or 'modern programming languages'}. [{readme_sid}] "
            f"{first_readme_para} [{readme_sid}]"
        )

        # 2. Architecture at a glance
        arch_lines = [
            f"The codebase uses **{frameworks}** for its application logic and **{databases}** for persistence. [{readme_sid}]",
            "The repository is organized into distinct functional layers:",
        ]
        top_dirs = sorted({f.split("/")[0] for f in file_metrics.keys() if "/" in f})
        for d in top_dirs:
            # find a source in that dir
            d_sources = [sid for path, sid in path_to_sid.items() if path.startswith(f"{d}/")]
            cite = f" [{d_sources[0]}]" if d_sources else ""
            arch_lines.append(
                f"- **`{d}/`**: Component layer containing domain modules and services.{cite}"
            )

        # 3. Key modules
        key_modules_lines = []
        for mod in top_ranked:
            sid = path_to_sid.get(mod)
            cite = f" [{sid}]" if sid else ""
            pr = file_metrics[mod].get("pagerank", 0.0)
            fan_in = file_metrics[mod].get("fan_in", 0)
            key_modules_lines.append(
                f"- **`{mod}`**: Central dependency with high incoming centrality (fan-in: {fan_in}, PageRank: {pr:.4f}).{cite}"
            )

        # 4. How a request flows
        flow_lines = [
            "Execution flows sequentially through the application hierarchy:",
        ]
        step = 1
        for ep in entry_points[:3]:
            sid = path_to_sid.get(ep["path"])
            cite = f" [{sid}]" if sid else ""
            flow_lines.append(
                f"{step}. **Ingress & Bootstrap**: `{ep['path']}` initiates application runtime.{cite}"
            )
            step += 1

        for mod in top_ranked[:2]:
            sid = path_to_sid.get(mod)
            cite = f" [{sid}]" if sid else ""
            flow_lines.append(
                f"{step}. **Domain Processing**: Requests delegate to core logic in `{mod}`.{cite}"
            )
            step += 1

        # 5. How to run
        run_lines = [
            "The repository contains standard execution entry points and configuration files:",
        ]
        for ep in entry_points:
            sid = path_to_sid.get(ep["path"])
            cite = f" [{sid}]" if sid else ""
            run_lines.append(f"- Run `{ep['path']}`: {ep.get('description', 'Entrypoint')}.{cite}")

        # 6. Where to start
        start_lines = [
            "Recommended onboarding reading sequence to understand the codebase:",
        ]
        for item in reading_order[:8]:
            sid = path_to_sid.get(item["path"])
            cite = f" [{sid}]" if sid else ""
            start_lines.append(f"{item['step']}. **`{item['path']}`**: {item['reason']}.{cite}")

        sections = [
            "## What this project is\n\n" + what_it_is,
            "## Architecture at a glance\n\n" + "\n".join(arch_lines),
            "## Key modules\n\n"
            + "\n".join(key_modules_lines or ["- Core modules discovered in project root."]),
            "## How a request flows\n\n" + "\n".join(flow_lines),
            "## How to run\n\n" + "\n".join(run_lines),
            "## Where to start\n\n" + "\n".join(start_lines),
        ]

        markdown = "\n\n".join(sections)
        questions = self._default_questions(entry_points, file_metrics)
        return markdown, questions

    def _default_questions(
        self,
        entry_points: list[dict[str, Any]],
        file_metrics: dict[str, dict[str, Any]],
    ) -> list[str]:
        """Produces 6-8 tailored questions for the repository."""
        questions = [
            "Where is authentication and security implemented in this codebase?",
            "How does a request flow from the entry point to the database?",
            "What is the overall architecture and folder structure of this repository?",
            "How do I set up and run this project locally?",
            "What external packages and dependencies are used by this system?",
        ]
        if entry_points:
            questions.append(
                f"What happens during application startup in `{entry_points[0]['path']}`?"
            )

        top_files = sorted(
            [f for f, m in file_metrics.items() if m.get("pagerank", 0.0) > 0],
            key=lambda f: file_metrics[f].get("pagerank", 0.0),
            reverse=True,
        )
        if top_files:
            questions.append(
                f"What is the responsibility of `{top_files[0]}` and which modules import it?"
            )

        return questions[:8]
