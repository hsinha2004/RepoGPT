"""
Secret detectors for RepoGPT redaction service (§8.3).
Table-driven pattern matchers and generic high-entropy assignment detector.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass


def shannon_entropy(s: str) -> float:
    """Computes the Shannon entropy of a given string in bits per character."""
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


@dataclass
class MatchSpan:
    start: int
    end: int
    detector: str
    replacement: str | None = None  # Custom replacement if not default


# Detector regex definitions
# 1. AWS Access Key IDs: AKIA or ASIA followed by 16 alphanumeric characters
AWS_KEY_RE = re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")

# 2. GitHub Tokens: personal access tokens, OAuth tokens, new format fine-grained tokens
GITHUB_TOKEN_RE = re.compile(
    r"\b(gh[pousr]_[A-Za-z0-9_]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b"
)

# 3. GitLab Tokens
GITLAB_TOKEN_RE = re.compile(r"\bglpat-[0-9a-zA-Z_\-]{20,}\b")

# 4. Slack Tokens
SLACK_TOKEN_RE = re.compile(r"\bxox[abprs]-[0-9a-zA-Z]{10,48}\b")

# 5. Google API Keys: AIzaSy followed by characters
GOOGLE_API_KEY_RE = re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")

# 6. Stripe API Keys: sk_live_ or rk_live_
STRIPE_KEY_RE = re.compile(r"\b(?:sk|rk)_live_[0-9a-zA-Z]{24,}\b")

# 7. OpenAI and Anthropic API Keys: sk- or sk-ant-
OPENAI_KEY_RE = re.compile(r"\bsk-(?:live-|ant-)?[0-9a-zA-Z_\-]{20,}\b")

# 8. SendGrid API Keys
SENDGRID_KEY_RE = re.compile(r"\bSG\.[0-9a-zA-Z_\-\.]{22,64}\b")

# 9. Twilio API Keys
TWILIO_KEY_RE = re.compile(r"\bSK[0-9a-fA-F]{32}\b")

# 10. JWTs: three base64url-encoded segments starting with eyJ
JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-\.]{10,}\b")

# 11. PEM Private Key Blocks: entire block from BEGIN to END
PEM_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"
)

# 12. Connection strings with embedded credentials: scheme://user:pass@host
CONN_STRING_RE = re.compile(
    r"""(?x)
    \b[a-zA-Z][a-zA-Z0-9+.\-]*://
    (?P<user>[^:\s@/]+):
    (?P<pass>[^@\s/]+)
    @(?P<host>[^/\s:]+)
    """
)

# 13. Generic high-entropy secret assignment
GENERIC_ASSIGNMENT_RE = re.compile(
    r"""(?xi)
    (?P<prefix>
        (?P<key>\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret|auth)\b)
        \s*[:=]\s*
        (?P<quote>['"])
    )
    (?P<val>[^'"\r\n]{8,})
    (?P<suffix>(?P=quote))
    """
)

KNOWN_PLACEHOLDERS = {
    "changeme",
    "password",
    "secret",
    "your-password",
    "your-secret",
    "your-api-key",
    "your-token",
    "mysecretpassword",
    "example-key",
    "placeholder",
    "undefined",
    "null",
    "true",
    "false",
}


def find_known_secrets(text: str) -> list[MatchSpan]:
    """Finds all occurrences of known-format secrets."""
    spans: list[MatchSpan] = []

    # PEM Private Keys (handles multiline replacement preserving newline count)
    for m in PEM_PRIVATE_KEY_RE.finditer(text):
        matched_str = m.group(0)
        newline_count = matched_str.count("\n")
        # Keep newline count so subsequent line numbers are strictly preserved
        rep = f"<REDACTED_SECRET:pem_private_key>{newline_count * chr(10)}"
        spans.append(
            MatchSpan(
                start=m.start(),
                end=m.end(),
                detector="pem_private_key",
                replacement=rep,
            )
        )

    # Connection Strings (redact just the password part: scheme://user:<REDACTED>@host)
    for m in CONN_STRING_RE.finditer(text):
        pass_start = m.start("pass")
        pass_end = m.end("pass")
        pass_val = m.group("pass")
        # Only redact if not obvious placeholder
        if pass_val.lower() not in KNOWN_PLACEHOLDERS and not pass_val.startswith("${"):
            spans.append(
                MatchSpan(
                    start=pass_start,
                    end=pass_end,
                    detector="connection_string",
                    replacement="<REDACTED_SECRET:connection_string>",
                )
            )

    # Simple regex matches
    regex_detectors = [
        ("aws_access_key", AWS_KEY_RE),
        ("github_token", GITHUB_TOKEN_RE),
        ("gitlab_token", GITLAB_TOKEN_RE),
        ("slack_token", SLACK_TOKEN_RE),
        ("google_api_key", GOOGLE_API_KEY_RE),
        ("stripe_key", STRIPE_KEY_RE),
        ("openai_anthropic_key", OPENAI_KEY_RE),
        ("sendgrid_key", SENDGRID_KEY_RE),
        ("twilio_key", TWILIO_KEY_RE),
        ("jwt", JWT_RE),
    ]

    for name, pattern in regex_detectors:
        for m in pattern.finditer(text):
            spans.append(
                MatchSpan(
                    start=m.start(),
                    end=m.end(),
                    detector=name,
                    replacement=f"<REDACTED_SECRET:{name}>",
                )
            )

    return spans


def find_generic_secrets(text: str) -> list[MatchSpan]:
    """
    Finds generic high-entropy secret assignments.
    Condition: key matches sensitive words, quoted value >= 8 chars, entropy >= 3.5,
    excluding common placeholders.
    """
    spans: list[MatchSpan] = []
    for m in GENERIC_ASSIGNMENT_RE.finditer(text):
        val = m.group("val")
        val_lower = val.lower()

        # Filter out common placeholders and template variables
        if (
            val_lower in KNOWN_PLACEHOLDERS
            or val_lower.startswith("your-")
            or val_lower.startswith("xxx")
            or val_lower.startswith("<")
            or val_lower.startswith("${")
            or val_lower.startswith("os.environ")
            or val_lower.startswith("process.env")
            or "changeme" in val_lower
        ):
            continue

        entropy = shannon_entropy(val)
        if entropy >= 3.5:
            val_start = m.start("val")
            val_end = m.end("val")
            spans.append(
                MatchSpan(
                    start=val_start,
                    end=val_end,
                    detector="generic_secret",
                    replacement="<REDACTED_SECRET:generic_secret>",
                )
            )

    return spans
