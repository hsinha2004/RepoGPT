import pytest
from app.services.retrieval.router.heuristic import route_heuristically

ROUTER_TEST_CASES = [
    # 1. Locate intent
    ("Where is AuthService.login defined?", "locate"),
    ("find function verify_password", "locate"),
    ("where is create_access_token implemented", "locate"),
    ("which file defines TaskRepository", "locate"),
    ("show me the implementation of get_db", "locate"),
    ("where is send_reminder implemented?", "locate"),
    ("find class ReportGenerator", "locate"),
    ("which file contains CsvExporter?", "locate"),
    ("where is StartScheduler in Go worker?", "locate"),
    ("AuthService.login", "locate"),
    ("app/auth/security.py", "locate"),
    ("backend/app/main.py", "locate"),
    ("find endpoint create_task", "locate"),
    ("where is `decode_token`?", "locate"),

    # 2. Explain intent
    ("explain what TaskService.list_overdue does", "explain"),
    ("what does verify_password do?", "explain"),
    ("how does create_access_token work?", "explain"),
    ("walk me through TaskRepository.search", "explain"),
    ("purpose of ReportGenerator class", "explain"),
    ("explain the authentication flow in auth/security.py", "explain"),
    ("what does send_reminder function do?", "explain"),

    # 3. Flow intent
    ("How does a request to create a task move from the React page to the database?", "flow"),
    ("trace a request from login endpoint to database check", "flow"),
    ("what is the request lifecycle for creating a task?", "flow"),
    ("how does the call chain look from API to database?", "flow"),
    ("trace execution from frontend to reminder worker", "flow"),
    ("how does authentication data flow through the application?", "flow"),

    # 4. Architecture intent
    ("What is the high-level architecture of this repository?", "architecture"),
    ("how is the project structured and organized?", "architecture"),
    ("overview of the codebase and system design", "architecture"),
    ("what is the tech stack used in this project?", "architecture"),
    ("explain the directory structure and main modules", "architecture"),
    ("high level overview of backend and frontend", "architecture"),

    # 5. Dependency intent
    ("what modules depend on app/db.py?", "dependency"),
    ("who calls TaskService.complete_task?", "dependency"),
    ("what imports backend/app/config.py?", "dependency"),
    ("callers of verify_password", "dependency"),
    ("what packages does the Go worker depend on?", "dependency"),
    ("show dependencies and incoming calls for TaskRepository", "dependency"),

    # 6. Config intent
    ("how to run the project with docker?", "config"),
    ("how to start the development servers?", "config"),
    ("how do I configure environment variables in .env?", "config"),
    ("how to install dependencies and prerequisites?", "config"),
    ("where is docker-compose configuration located?", "config"),
    ("how to deploy this application?", "config"),

    # 7. General programming concepts
    ("what is a closure in javascript?", "general"),
    ("how does quicksort work?", "general"),
    ("explain list comprehension in python", "general"),
    ("difference between process and thread", "general"),

    # 8. Out of scope / conversational
    ("hello, how are you?", "out_of_scope"),
    ("hey there", "out_of_scope"),
    ("what is the weather in Paris today?", "out_of_scope"),
    ("tell me a funny joke", "out_of_scope"),
    ("write a poem about computers", "out_of_scope"),
]


@pytest.mark.parametrize("query,expected_intent", ROUTER_TEST_CASES)
def test_router_heuristics_table(query: str, expected_intent: str) -> None:
    res = route_heuristically(query)
    assert res.intent == expected_intent, f"Failed for query: '{query}' -> got {res.intent}, expected {expected_intent}"


def test_router_reason_word_count() -> None:
    for query, _ in ROUTER_TEST_CASES:
        res = route_heuristically(query)
        words = res.reason.split()
        assert len(words) <= 25, f"Reason exceeded 25 words: '{res.reason}' ({len(words)} words)"


def test_router_weights_and_enrichment_flags() -> None:
    # Locate intent should lean towards BM25 and have symbol_lookup enabled
    loc_res = route_heuristically("where is AuthService.login defined?")
    assert loc_res.weights.bm25 >= loc_res.weights.vector
    assert loc_res.enrich.symbol_lookup is True

    # Flow intent should have graph_expand enabled
    flow_res = route_heuristically("how does request flow from React to DB?")
    assert flow_res.enrich.graph_expand is True

    # Architecture intent should have summary_scope enabled
    arch_res = route_heuristically("what is the high-level architecture of this repo?")
    assert arch_res.enrich.summary_scope is True

    # Out of scope should disable all enrichments
    oos_res = route_heuristically("hello there")
    assert oos_res.enrich.symbol_lookup is False
    assert oos_res.enrich.graph_expand is False
    assert oos_res.enrich.summary_scope is False
