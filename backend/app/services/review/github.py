"""
GitHub integration client for PR reviews and publishing (§10.1, §10.5).
Pure HTTP via httpx; never runs git binary or merges/approves.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

GITHUB_PR_REGEX = re.compile(
    r"^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/pull/(\d+)/?$"
)


def parse_github_pr_url(url: str) -> tuple[str, str, int] | None:
    """Parses owner, repo, and pull_number from a GitHub PR URL."""
    match = GITHUB_PR_REGEX.match(url.strip())
    if not match:
        return None
    return match.group(1), match.group(2), int(match.group(3))


class GitHubReviewClient:
    """
    Interacts with GitHub REST API for pull requests and review comments.
    """

    def __init__(self, api_url: str = "https://api.github.com", token: str | None = None) -> None:
        self.api_url = api_url.rstrip("/")
        self.token = token

    def _headers(self, custom_token: str | None = None) -> dict[str, str]:
        tok = custom_token or self.token
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoGPT-CodeReview/1.0",
        }
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        return headers

    async def fetch_pr_details(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        custom_token: str | None = None,
    ) -> dict[str, Any]:
        """Fetches PR metadata (title, body, base SHA, head SHA)."""
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self._headers(custom_token))
            if resp.status_code != 200:
                raise ValueError(f"GitHub API error ({resp.status_code}): {resp.text}")
            return resp.json()

    async def fetch_pr_diff(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        custom_token: str | None = None,
    ) -> str:
        """Fetches unified diff for the PR."""
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = self._headers(custom_token)
        headers["Accept"] = "application/vnd.github.v3.diff"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch PR diff ({resp.status_code}): {resp.text}")
            return resp.text

    async def publish_review_comments(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        summary: str,
        accepted_findings: list[dict[str, Any]],
        custom_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Publishes accepted review findings as a COMMENT review (§10.5).
        Never approves or requests changes.
        """
        if not custom_token and not self.token:
            raise ValueError("GitHub personal access token (PAT) required to publish reviews.")

        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"

        comments: list[dict[str, Any]] = []
        for f in accepted_findings:
            body_parts = [
                f"**[{f['severity'].upper()}] {f['title']}** ({f['category']})",
                "",
                f"{f['explanation']}",
            ]
            if f.get("suggestion"):
                body_parts.extend(["", f"💡 **Suggestion:** {f['suggestion']}"])
            if f.get("suggested_code"):
                body_parts.extend(["", "```suggestion", f["suggested_code"], "```"])

            comments.append({
                "path": f["path"],
                "line": f["end_line"],
                "side": f.get("side", "RIGHT"),
                "body": "\n".join(body_parts),
            })

        payload = {
            "body": summary or "Automated review findings generated via RepoGPT.",
            "event": "COMMENT",  # Mandatory requirement (§10.5)
            "comments": comments,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=self._headers(custom_token), json=payload)
            if resp.status_code not in {200, 201}:
                raise ValueError(f"Failed to post GitHub review ({resp.status_code}): {resp.text}")
            return resp.json()
