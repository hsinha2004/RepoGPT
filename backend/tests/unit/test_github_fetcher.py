"""
Unit tests for GitHub URL parsing, validation, and SSRF prevention (§8.1).
"""

import pytest

from app.core.errors import ValidationFailedError
from app.services.ingestion.github_fetcher import parse_github_url


def test_parse_valid_github_urls():
    assert parse_github_url("https://github.com/fastapi/fastapi") == ("fastapi", "fastapi", None)
    assert parse_github_url("https://github.com/fastapi/fastapi.git") == (
        "fastapi",
        "fastapi",
        None,
    )
    assert parse_github_url("https://github.com/pallets/flask/tree/2.3.x") == (
        "pallets",
        "flask",
        "2.3.x",
    )
    assert parse_github_url("psf/requests") == ("psf", "requests", None)
    assert parse_github_url("psf/requests#v2.32.3") == ("psf", "requests", "v2.32.3")


def test_reject_ssrf_and_invalid_urls():
    invalid_cases = [
        "http://malicious-site.com/repo",
        "file:///etc/passwd",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost:8000/repo",
        "https://gitlab.com/owner/repo",
        "https://github.com/owner",  # Missing repo
        "https://github.com/../../etc/passwd",
        "javascript:alert(1)",
    ]

    for bad_url in invalid_cases:
        with pytest.raises(ValidationFailedError):
            parse_github_url(bad_url)
