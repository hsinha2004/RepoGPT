"""
Code-aware Tokenizer for BM25 Keyword Search (§8.7).

Follows §8.7 specifications:
- lower-case
- split on non-alphanumerics
- split camelCase, PascalCase, snake_case, kebab-case and digits into parts AND keep original compound token
- drop tokens shorter than 2 chars
- small stop-word list (English + common language keywords)
- path segments added twice (path boost)
"""

import re

# Small stop-word list: English stop words + common programming language keywords
STOP_WORDS: frozenset[str] = frozenset(
    {
        # English stop words
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "if",
        "in",
        "into",
        "is",
        "it",
        "no",
        "not",
        "of",
        "on",
        "or",
        "such",
        "that",
        "the",
        "their",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "was",
        "will",
        "with",
        # Common language keywords (Python, JS/TS, Java, Go, C/C++)
        "def",
        "return",
        "const",
        "let",
        "var",
        "public",
        "private",
        "protected",
        "class",
        "function",
        "func",
        "import",
        "export",
        "from",
        "self",
        "package",
        "struct",
        "interface",
        "type",
        "void",
        "async",
        "await",
        "static",
        "final",
        "true",
        "false",
        "null",
        "none",
        "nil",
        "new",
        "throw",
        "throws",
        "try",
        "catch",
        "finally",
        "except",
        "while",
        "do",
        "switch",
        "case",
        "break",
        "continue",
        "default",
        "else",
        "elif",
    }
)


def split_subtokens(text: str) -> list[str]:
    """
    Splits camelCase, PascalCase, snake_case, kebab-case, and digits into constituent parts.
    Example:
        'getUserById' -> ['get', 'user', 'by', 'id']
        'user_profile' -> ['user', 'profile']
        'user-profile' -> ['user', 'profile']
        'HTTP2Client'  -> ['http', '2', 'client']
    """
    # 1. Lowercase followed by Uppercase (e.g. camelCase, PascalCase)
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    # 2. Acronym followed by capitalized word (e.g. XMLParser -> XML Parser)
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s1)
    # 3. Letters followed by digits and digits followed by letters
    s3 = re.sub(r"([a-zA-Z])([0-9])", r"\1 \2", s2)
    s4 = re.sub(r"([0-9])([a-zA-Z])", r"\1 \2", s3)
    # 4. Split on non-alphanumeric characters (including hyphens and underscores)
    parts = re.split(r"[^a-zA-Z0-9]+", s4)
    return [p.lower() for p in parts if p]


def tokenize_code(text: str, file_path: str | None = None) -> list[str]:
    """
    Tokenizes code text with code-aware splitting, stop-word removal, and path boosting.
    """
    tokens: list[str] = []

    # If file_path is not explicitly given, try extracting from 'File: <path>' header
    if not file_path:
        match = re.match(r"^File:\s*([^\s(]+)", text)
        if match:
            file_path = match.group(1)

    # 1. Path boost: split path into segments and add resulting tokens twice
    if file_path:
        # Split on path delimiters and extension dots
        segments = re.split(r"[\\/.]+", file_path)
        for seg in segments:
            if not seg:
                continue
            compound = seg.lower()
            path_tokens: list[str] = []
            if len(compound) >= 2 and compound not in STOP_WORDS:
                path_tokens.append(compound)
            subparts = split_subtokens(seg)
            for part in subparts:
                if len(part) >= 2 and part not in STOP_WORDS and part != compound:
                    path_tokens.append(part)
            # Add each path token twice (path boost)
            for t in path_tokens:
                tokens.extend([t, t])

    # 2. Tokenize text body: extract candidates that might contain hyphens/underscores
    candidates = re.findall(r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*", text)
    for cand in candidates:
        compound = cand.lower()
        if len(compound) >= 2 and compound not in STOP_WORDS:
            tokens.append(compound)

        # Subparts from camelCase, snake_case, kebab-case, digits
        subparts = split_subtokens(cand)
        for part in subparts:
            if len(part) >= 2 and part not in STOP_WORDS and part != compound:
                tokens.append(part)

    return tokens
