"""
GitHub API integration, URL validation, and archive streaming (§8.1).
Defends against SSRF by strictly enforcing github.com and codeload.github.com hosts.
"""

import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from app.core.config import get_settings
from app.core.errors import (
    AppError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
    ValidationFailedError,
)

logger = structlog.get_logger(__name__)

# Strict regex patterns for owner, repo, ref
OWNER_REGEX = re.compile(r"^[A-Za-z0-9-]{1,39}$")
REPO_REGEX = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
REF_REGEX = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")

GITHUB_URL_REGEX = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9-]{1,39})/(?P<repo>[A-Za-z0-9._-]{1,100}?)(?:\.git)?(?:/tree/(?P<ref>[A-Za-z0-9._/-]{1,100}))?/?$"
)
SHORTHAND_REGEX = re.compile(
    r"^(?P<owner>[A-Za-z0-9-]{1,39})/(?P<repo>[A-Za-z0-9._-]{1,100})(?:#(?P<ref>[A-Za-z0-9._/-]{1,100}))?$"
)


def parse_github_url(url_or_shorthand: str) -> tuple[str, str, str | None]:
    """
    Parses and strictly validates a GitHub repository identifier.
    Accepts:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo/tree/branch-or-tag
      - owner/repo or owner/repo#ref
    Rejects any non-GitHub URL, file://, localhost, or IP addresses (SSRF defense).
    """
    cleaned = url_or_shorthand.strip()
    match = GITHUB_URL_REGEX.match(cleaned)
    if match:
        owner = match.group("owner")
        repo = match.group("repo")
        if repo.endswith(".git"):
            repo = repo[:-4]
        ref = match.group("ref")
        return owner, repo, ref

    match = SHORTHAND_REGEX.match(cleaned)
    if match:
        owner = match.group("owner")
        repo = match.group("repo")
        ref = match.group("ref")
        return owner, repo, ref

    raise ValidationFailedError(
        f"Invalid GitHub repository identifier: '{url_or_shorthand}'. "
        "Expected format: 'https://github.com/owner/repo' or 'owner/repo'."
    )


class GitHubFetcher:
    def __init__(self, pat: str | None = None) -> None:
        self.settings = get_settings()
        self.pat = pat or self.settings.GITHUB_TOKEN
        self.base_url = self.settings.GITHUB_API_URL.rstrip("/")

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "RepoGPT-Ingestion/1.0",
        }
        if self.pat:
            headers["Authorization"] = f"Bearer {self.pat}"
        return headers

    async def fetch_repo_metadata(self, owner: str, repo: str) -> dict[str, Any]:
        """
        Fetches metadata for the repository via GitHub REST API.
        Enforces maximum repository size limits and handles rate limits.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._get_headers())

            if resp.status_code == 404:
                raise NotFoundError(
                    f"Repository '{owner}/{repo}' not found or is private. "
                    "If this is a private repository, please configure a GitHub Personal Access Token in Settings."
                )
            if resp.status_code in (401, 403):
                rate_remaining = resp.headers.get("x-ratelimit-remaining")
                if rate_remaining == "0":
                    reset_time = int(resp.headers.get("x-ratelimit-reset", "0"))
                    raise RateLimitedError(
                        f"GitHub API rate limit exceeded. Resets at epoch {reset_time}.",
                        retry_after=60,
                    )
                raise UnauthorizedError(
                    f"Access denied to GitHub repository '{owner}/{repo}'. "
                    "Verify your GitHub PAT has the 'repo' scope."
                )
            if resp.status_code >= 400:
                raise AppError(
                    f"GitHub API returned error {resp.status_code}: {resp.text}",
                    status_code=resp.status_code,
                )

            data = resp.json()
            size_kb = data.get("size", 0)
            size_mb = size_kb / 1024
            if size_mb > self.settings.MAX_REPO_SIZE_MB:
                raise ValidationFailedError(
                    f"Repository size ({size_mb:.1f} MB) exceeds maximum allowed limit of {self.settings.MAX_REPO_SIZE_MB} MB."
                )

            return {
                "owner": data["owner"]["login"],
                "name": data["name"],
                "full_name": data["full_name"],
                "description": data.get("description") or "",
                "is_private": data.get("private", False),
                "default_branch": data.get("default_branch", "main"),
                "size_kb": size_kb,
                "html_url": data.get("html_url", f"https://github.com/{owner}/{repo}"),
            }

    async def resolve_commit_sha(self, owner: str, repo: str, ref: str) -> str:
        """
        Resolves a branch name, tag, or partial ref to its full 40-character commit SHA.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{ref}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 404:
                raise NotFoundError(
                    f"Ref or commit '{ref}' not found in repository '{owner}/{repo}'."
                )
            if resp.status_code >= 400:
                raise AppError(
                    f"Failed to resolve commit SHA for '{ref}': {resp.text}",
                    status_code=resp.status_code,
                )

            data = resp.json()
            sha = data.get("sha")
            if not sha or len(sha) < 7:
                raise AppError(f"Unexpected commit payload from GitHub API for ref '{ref}'.")
            return sha

    async def download_tarball(
        self,
        owner: str,
        repo: str,
        sha: str,
        target_path: str,
    ) -> int:
        """
        Streams tarball from GitHub with redirect validation and size caps.
        Only redirects to codeload.github.com are followed (SSRF defense).
        """
        initial_url = f"{self.base_url}/repos/{owner}/{repo}/tarball/{sha}"
        max_bytes = self.settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024

        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        total_downloaded = 0

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
            resp = await client.get(initial_url, headers=self._get_headers())

            download_url = initial_url
            if resp.status_code in (301, 302, 307, 308):
                redirect_target = resp.headers.get("location")
                if not redirect_target:
                    raise AppError(
                        "GitHub tarball request returned redirect without Location header."
                    )

                parsed = urlparse(redirect_target)
                if parsed.hostname != "codeload.github.com":
                    raise AppError(
                        f"Refusing redirect to untrusted host '{parsed.hostname}'. Expected 'codeload.github.com'."
                    )
                download_url = redirect_target

            # Stream download
            async with client.stream(
                "GET", download_url, headers=self._get_headers()
            ) as stream_resp:
                if stream_resp.status_code >= 400:
                    raise AppError(
                        f"Failed to download tarball from GitHub: HTTP {stream_resp.status_code}",
                        status_code=stream_resp.status_code,
                    )

                with open(target_path, "wb") as f:
                    async for chunk in stream_resp.aiter_bytes(chunk_size=65536):
                        total_downloaded += len(chunk)
                        if total_downloaded > max_bytes:
                            f.close()
                            if os.path.exists(target_path):
                                os.remove(target_path)
                            raise ValidationFailedError(
                                f"Downloaded archive exceeded maximum limit of {self.settings.MAX_DOWNLOAD_SIZE_MB} MB."
                            )
                        f.write(chunk)

        logger.info(
            "downloaded_github_tarball",
            owner=owner,
            repo=repo,
            sha=sha,
            bytes=total_downloaded,
        )
        return total_downloaded
