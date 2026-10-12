"""
Core Review Service coordinating diff parsing, symbol mapping, LangGraph execution,
finding persistence, and export/publishing (§10).
"""

from __future__ import annotations

from typing import Any

import structlog

from app.agents.review_graph import ReviewGraphRunner, ReviewGraphState
from app.core.config import Settings, get_settings
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.db.repositories.files import FileRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.reviews import ReviewRepository
from app.db.repositories.symbols import SymbolRepository
from app.services.review.context import ReviewContextBuilder
from app.services.review.diff_parser import apply_patch_to_text, parse_unified_diff
from app.services.review.github import GitHubReviewClient, parse_github_pr_url
from app.services.review.static_analysis import StaticAnalyzer

logger = structlog.get_logger(__name__)


class ReviewService:
    """
    Coordinates end-to-end pull request and diff review processing.
    """

    def __init__(
        self,
        review_repo: ReviewRepository,
        repo_repo: RepositoryRepository,
        file_repo: FileRepository,
        symbol_repo: SymbolRepository,
        runner: ReviewGraphRunner | None = None,
        context_builder: ReviewContextBuilder | None = None,
        static_analyzer: StaticAnalyzer | None = None,
        github_client: GitHubReviewClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.review_repo = review_repo
        self.repo_repo = repo_repo
        self.file_repo = file_repo
        self.symbol_repo = symbol_repo
        self.runner = runner or ReviewGraphRunner()
        self.context_builder = context_builder or ReviewContextBuilder(symbol_repo, file_repo)
        self.static_analyzer = static_analyzer or StaticAnalyzer()
        self.github_client = github_client or GitHubReviewClient()
        self.settings = settings or get_settings()

    async def create_review_from_diff(
        self,
        repo_id: str,
        user_id: str,
        diff_text: str,
        patch_filename: str = "uploaded.patch",
        source: dict[str, Any] | None = None,
        indexed_commit_mismatch: bool = False,
    ) -> dict[str, Any]:
        """
        Processes a raw diff/patch upload against an indexed repository (§10.1).
        """
        repo_doc = await self.repo_repo.get_by_id(repo_id)
        if not repo_doc:
            raise NotFoundError(f"Repository {repo_id} not found.")

        # 1. Parse unified diff
        parsed_diffs = parse_unified_diff(diff_text)
        if not parsed_diffs:
            raise BadRequestError("No valid file diffs or hunks found in provided patch.")

        # 2. Create pending review document in database
        review_source = source or {
            "type": "upload",
            "patch_filename": patch_filename,
        }
        review_doc = await self.review_repo.create_review(
            repo_id=repo_id,
            user_id=user_id,
            source=review_source,
            indexed_commit_mismatch=indexed_commit_mismatch,
        )
        review_id = str(review_doc["_id"])

        # 3. Build file representations & context
        diff_dicts: list[dict[str, Any]] = []
        file_contexts: dict[str, list[dict[str, Any]]] = {}
        file_symbols: dict[str, list[dict[str, Any]]] = {}
        static_results: dict[str, list[dict[str, Any]]] = {}

        for pd in parsed_diffs:
            path = pd.path
            base_file_doc = await self.file_repo.get_by_path(repo_id, path)
            base_content = base_file_doc.get("content", "") if base_file_doc else ""

            # Compute head content by applying patch (pure Python, §10.2)
            head_content = apply_patch_to_text(base_content, pd)

            # Map hunks to symbols via tree-sitter
            mapped_syms = await self.context_builder.map_symbols(
                repo_id=repo_id,
                path=path,
                head_content=head_content,
                file_diff=pd,
            )
            file_symbols[path] = mapped_syms

            # Retrieve context (callers, related tests, conventions)
            ctx = await self.context_builder.retrieve_file_context(
                repo_id=repo_id,
                path=path,
                changed_symbols=mapped_syms,
            )
            file_contexts[path] = ctx

            # Run isolated static analysis on changed lines
            static_issues = self.static_analyzer.analyze_python_file(
                path=path,
                head_content=head_content,
                changed_lines=pd.changed_new_lines,
            )
            static_results[path] = static_issues

            diff_dicts.append({
                "path": path,
                "old_path": pd.old_path,
                "is_added": pd.is_added,
                "is_deleted": pd.is_deleted,
                "is_modified": pd.is_modified,
                "added_line_count": pd.added_line_count,
                "deleted_line_count": pd.deleted_line_count,
                "changed_new_lines": pd.changed_new_lines,
                "hunks": [
                    {
                        "old_start": h.old_start,
                        "old_length": h.old_length,
                        "new_start": h.new_start,
                        "new_length": h.new_length,
                        "raw_lines": h.raw_lines,
                        "added_lines": h.added_lines,
                        "deleted_lines": h.deleted_lines,
                    }
                    for h in pd.hunks
                ],
            })

        # 4. Execute LangGraph Review Graph
        state: ReviewGraphState = {
            "repo_id": repo_id,
            "pr_title": f"Review {patch_filename}",
            "pr_description": f"Diff review of {len(parsed_diffs)} file(s)",
            "file_diffs": diff_dicts,
            "file_contexts": file_contexts,
            "file_symbols": file_symbols,
            "static_analysis_results": static_results,
        }

        try:
            result_state = await self.runner.run(state)
            # Update review record in MongoDB
            updated = await self.review_repo.update_results(
                review_id=review_id,
                status="completed",
                risk_level=result_state.get("risk_level", "low"),
                stats=result_state.get("stats", {}),
                summary=result_state.get("summary", ""),
                file_walkthrough=result_state.get("file_walkthrough", []),
                findings=result_state.get("validated_findings", []),
                general_comments=result_state.get("general_comments", []),
            )
            return updated or review_doc
        except Exception as exc:
            logger.error("review_graph_execution_failed", review_id=review_id, error=str(exc))
            await self.review_repo.update_results(
                review_id=review_id,
                status="failed",
                risk_level="low",
                stats={},
                summary="",
                file_walkthrough=[],
                findings=[],
                general_comments=[],
                error=str(exc),
            )
            raise

    async def create_review_from_pr(
        self,
        repo_id: str,
        user_id: str,
        pr_url: str,
        custom_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetches GitHub PR diff and executes review workflow (§10.1).
        """
        parsed_pr = parse_github_pr_url(pr_url)
        if not parsed_pr:
            raise BadRequestError("Invalid GitHub pull request URL. Must be https://github.com/{owner}/{repo}/pull/{number}")

        owner, repo_name, pr_num = parsed_pr
        pr_details = await self.github_client.fetch_pr_details(owner, repo_name, pr_num, custom_token)
        diff_text = await self.github_client.fetch_pr_diff(owner, repo_name, pr_num, custom_token)

        # Check commit mismatch against indexed commit
        repo_doc = await self.repo_repo.get_by_id(repo_id)
        if not repo_doc:
            raise NotFoundError(f"Repository {repo_id} not found.")

        indexed_commit = repo_doc.get("last_synced_commit")
        base_sha = pr_details.get("base", {}).get("sha")
        head_sha = pr_details.get("head", {}).get("sha")
        mismatch = bool(indexed_commit and base_sha and indexed_commit != base_sha)

        parsed_diffs = parse_unified_diff(diff_text)
        if not parsed_diffs:
            raise BadRequestError("No valid file diffs found in GitHub pull request.")

        # Execute diff review
        return await self.create_review_from_diff(
            repo_id=repo_id,
            user_id=user_id,
            diff_text=diff_text,
            patch_filename=f"pr_{pr_num}.diff",
            source={
                "type": "github",
                "pr_number": pr_num,
                "pr_url": pr_url,
                "base_sha": base_sha,
                "head_sha": head_sha,
            },
            indexed_commit_mismatch=mismatch,
        )

    async def publish_to_github(
        self,
        review_id: str,
        user_id: str,
        custom_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Publishes accepted review findings to GitHub as a COMMENT review (§10.5).
        """
        review_doc = await self.review_repo.get_by_id(review_id)
        if not review_doc:
            raise NotFoundError(f"Review {review_id} not found.")

        if review_doc.get("user_id") != user_id:
            raise ForbiddenError("Access forbidden to this review.")

        source = review_doc.get("source", {})
        if source.get("type") != "github" or not source.get("pr_url"):
            raise BadRequestError("Only reviews created from GitHub PRs can be published to GitHub.")

        parsed_pr = parse_github_pr_url(source["pr_url"])
        if not parsed_pr:
            raise BadRequestError("Could not parse GitHub PR URL.")

        owner, repo_name, pr_num = parsed_pr
        findings = review_doc.get("findings", [])
        accepted_findings = [f for f in findings if f.get("status") in {"accepted", "edited"}]

        if not accepted_findings:
            raise BadRequestError("At least one accepted finding is required to publish review to GitHub.")

        res = await self.github_client.publish_review_comments(
            owner=owner,
            repo=repo_name,
            pull_number=pr_num,
            summary=review_doc.get("summary", ""),
            accepted_findings=accepted_findings,
            custom_token=custom_token,
        )

        gh_id = str(res.get("id", ""))
        gh_url = res.get("html_url", "")
        updated = await self.review_repo.mark_published(review_id, gh_id, gh_url)
        return updated or review_doc

    def export_markdown(self, review_doc: dict[str, Any]) -> str:
        """
        Exports a comprehensive markdown report for human sharing (§10.5).
        """
        lines = [
            f"# Code Review Report — {review_doc.get('source', {}).get('patch_filename', 'Pull Request')}",
            "",
            f"**Status:** `{review_doc.get('status', '').upper()}`  ",
            f"**Risk Level:** `{review_doc.get('risk_level', '').upper()}`  ",
            "",
            "## Summary",
            review_doc.get("summary", "No summary provided."),
            "",
            "## File Walkthrough",
        ]

        for item in review_doc.get("file_walkthrough", []):
            lines.append(
                f"- **`{item.get('path')}`**: +{item.get('added_lines', 0)} / -{item.get('deleted_lines', 0)} ({item.get('findings_count', 0)} findings)"
            )

        lines.extend(["", "## Actionable Findings", ""])
        for f in review_doc.get("findings", []):
            lines.extend([
                f"### [{f.get('severity', '').upper()}] {f.get('title')} ({f.get('category')})",
                f"**File:** `{f.get('path')}` (Lines {f.get('start_line')}–{f.get('end_line')})  ",
                f"**Status:** `{f.get('status', 'pending')}` | **Confidence:** {f.get('confidence', 0.8):.2f}",
                "",
                f.get("explanation", ""),
                "",
            ])
            if f.get("suggestion"):
                lines.extend([f"> **Suggestion:** {f.get('suggestion')}", ""])
            if f.get("suggested_code"):
                lines.extend(["```", f.get("suggested_code"), "```", ""])

        return "\n".join(lines)
