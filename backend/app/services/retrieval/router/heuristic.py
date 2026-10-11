from __future__ import annotations

import re

from app.schemas.retrieval import (
    RouterEnrich,
    RouteResult,
    RouterWeights,
)
from app.services.retrieval.symbol_lookup import extract_query_identifiers

# Out of scope patterns (greetings, unrelated topics)
OUT_OF_SCOPE_RE = re.compile(
    r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|howdy)\b|"
    r"\b(weather|poem|joke|recipe|capital\s+of|who\s+won|movie|song|lyrics)\b",
    re.IGNORECASE,
)

# General programming concepts (not referencing this repo)
GENERAL_CONCEPT_RE = re.compile(
    r"\b(what\s+is\s+a\s+(closure|decorator|generator|monad|pointer|goroutine|coroutine|promise)|"
    r"how\s+does\s+(quicksort|mergesort|binary\s+search|bubble\s+sort|dijkstra|garbage\s+collection)\s+work|"
    r"explain\s+(list\s+comprehension|big\s*o\s+notation|solid\s+principles|acid\s+properties)|"
    r"difference\s+between\s+(process\s+and\s+thread|stack\s+and\s+heap|interface\s+and\s+abstract\s+class))\b",
    re.IGNORECASE,
)

# Flow patterns
FLOW_RE = re.compile(
    r"\b(how\s+does\s+.+\s+(flow|move|propagate|travel)|"
    r"request\s+(lifecycle|path|flow)|call\s+chain|call\s+graph|trace\s+(a\s+)?request|"
    r"from\s+.+\s+to\s+.+|step\s*by\s*step\s+execution)\b",
    re.IGNORECASE,
)

# Architecture patterns
ARCHITECTURE_RE = re.compile(
    r"\b(architecture|high\s*level|system\s+design|tech\s+stack|how\s+is\s+(this|the)\s+(repo|project|codebase)\s+(structured|organized|laid\s+out)|"
    r"overview\s+of\s+(the\s+)?(repo|project|codebase)|project\s+structure|directory\s+structure)\b",
    re.IGNORECASE,
)

# Dependency patterns
DEPENDENCY_RE = re.compile(
    r"\b(depends?\s+on|dependencies|who\s+calls|what\s+calls|callers\s+of|used\s+by|imported\s+by|"
    r"what\s+imports|imports\s+of|incoming\s+calls|downstream\s+dependents)\b",
    re.IGNORECASE,
)

# Config patterns
CONFIG_RE = re.compile(
    r"\b(how\s+to\s+(run|start|install|setup|build|launch|deploy)|"
    r"docker|docker-compose|dockerfile|env\s+variables?|environment\s+variables?|"
    r"\.env|configuration|config\s+settings?|prerequisites?|requirements\.txt)\b",
    re.IGNORECASE,
)

# Locate patterns
LOCATE_RE = re.compile(
    r"\b(where\s+is|find\s+(the\s+)?(class|function|method|file|symbol|interface|endpoint)|"
    r"which\s+file\s+(contains|defines|implements|has)|show\s+me\s+(the\s+)?(definition|implementation))\b",
    re.IGNORECASE,
)

# Explain patterns
EXPLAIN_RE = re.compile(
    r"\b(explain|what\s+does\s+.+\s+do|how\s+does\s+.+\s+work|walk\s+me\s+through|purpose\s+of)\b",
    re.IGNORECASE,
)


def _truncate_reason(reason: str) -> str:
    """Ensures reason is at most 25 words."""
    words = reason.split()
    if len(words) <= 25:
        return reason
    return " ".join(words[:25])


def route_heuristically(query: str) -> RouteResult:
    """Classifies user queries into intents, strategies, weights, and enrichments using deterministic rules."""
    q_clean = query.strip()
    identifiers = extract_query_identifiers(q_clean)

    # 1. Out of scope
    if OUT_OF_SCOPE_RE.search(q_clean) and not any(
        "." in i or "(" in q_clean or "`" in q_clean for i in identifiers
    ):
        return RouteResult(
            intent="out_of_scope",
            strategy="hybrid",
            weights=RouterWeights(bm25=0.5, vector=0.5),
            enrich=RouterEnrich(symbol_lookup=False, graph_expand=False, summary_scope=False),
            identifiers=[],
            search_queries=[q_clean],
            reason=_truncate_reason("Query is conversational or unrelated to the repository."),
        )

    # 2. General programming question
    if GENERAL_CONCEPT_RE.search(q_clean) and not any("." in i for i in identifiers):
        return RouteResult(
            intent="general",
            strategy="hybrid",
            weights=RouterWeights(bm25=0.5, vector=0.5),
            enrich=RouterEnrich(symbol_lookup=False, graph_expand=False, summary_scope=False),
            identifiers=[],
            search_queries=[q_clean],
            reason=_truncate_reason("General programming question not specific to this codebase."),
        )

    # 3. Config / deployment intent
    if CONFIG_RE.search(q_clean):
        search_queries = [q_clean]
        if identifiers:
            search_queries.extend(identifiers[:2])
        return RouteResult(
            intent="config",
            strategy="hybrid",
            weights=RouterWeights(bm25=0.5, vector=0.5),
            enrich=RouterEnrich(symbol_lookup=True, graph_expand=False, summary_scope=False),
            identifiers=identifiers,
            search_queries=search_queries,
            reason=_truncate_reason(
                "Retrieving configuration, deployment instructions, and environment setup."
            ),
        )

    # 4. Flow intent
    if FLOW_RE.search(q_clean):
        search_queries = [q_clean]
        if identifiers:
            search_queries.extend(identifiers[:2])
        return RouteResult(
            intent="flow",
            strategy="hybrid_rerank",
            weights=RouterWeights(bm25=0.4, vector=0.6),
            enrich=RouterEnrich(symbol_lookup=True, graph_expand=True, summary_scope=False),
            identifiers=identifiers,
            search_queries=search_queries,
            reason=_truncate_reason(
                "Tracing execution flow and request lifecycle with graph expansion."
            ),
        )

    # 5. Architecture intent
    if ARCHITECTURE_RE.search(q_clean):
        return RouteResult(
            intent="architecture",
            strategy="vector",
            weights=RouterWeights(bm25=0.3, vector=0.7),
            enrich=RouterEnrich(symbol_lookup=False, graph_expand=False, summary_scope=True),
            identifiers=identifiers,
            search_queries=[q_clean, "overview architecture modules directory structure"],
            reason=_truncate_reason(
                "Analyzing high-level repository architecture and module organization."
            ),
        )

    # 6. Dependency intent
    if DEPENDENCY_RE.search(q_clean):
        search_queries = [q_clean]
        if identifiers:
            search_queries.extend(identifiers[:2])
        return RouteResult(
            intent="dependency",
            strategy="hybrid",
            weights=RouterWeights(bm25=0.5, vector=0.5),
            enrich=RouterEnrich(symbol_lookup=True, graph_expand=True, summary_scope=False),
            identifiers=identifiers,
            search_queries=search_queries,
            reason=_truncate_reason(
                "Inspecting component dependencies and import connections with graph expansion."
            ),
        )

    # 7. Locate intent
    if LOCATE_RE.search(q_clean) or (
        identifiers and len(q_clean.split()) <= 4 and not EXPLAIN_RE.search(q_clean)
    ):
        search_queries = [q_clean]
        if identifiers:
            search_queries.extend(identifiers[:2])
        return RouteResult(
            intent="locate",
            strategy="hybrid_rerank",
            weights=RouterWeights(bm25=0.6, vector=0.4),
            enrich=RouterEnrich(symbol_lookup=True, graph_expand=False, summary_scope=False),
            identifiers=identifiers,
            search_queries=search_queries,
            reason=_truncate_reason(
                "Locating symbol definition or file implementation via symbol lookup."
            ),
        )

    # 8. Explain intent
    search_queries = [q_clean]
    if identifiers:
        search_queries.extend(identifiers[:2])
    return RouteResult(
        intent="explain",
        strategy="hybrid_rerank",
        weights=RouterWeights(bm25=0.5, vector=0.5),
        enrich=RouterEnrich(
            symbol_lookup=bool(identifiers), graph_expand=False, summary_scope=False
        ),
        identifiers=identifiers,
        search_queries=search_queries,
        reason=_truncate_reason("Explaining codebase component implementation and functionality."),
    )
