from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.qa_graph import QAGraphRunner
from app.agents.state import QAState
from app.core.config import Settings
from app.services.llm.fake import FakeProvider


@pytest.fixture
def mock_retrieval_service():
    srv = MagicMock()
    srv.router = MagicMock()
    srv.keyword_search = MagicMock()
    srv.vector_search = MagicMock()
    srv.symbol_lookup = MagicMock()
    srv.summary_scope = MagicMock()
    srv.graph_expansion = MagicMock()
    srv.reranker = MagicMock()
    srv.reranker.rerank = AsyncMock(return_value=[0.9, 0.7])
    srv.chunk_repo = MagicMock()

    # Mock chunk retrieval
    async def mock_get_by_ids(_cids):
        return [
            {
                "_id": "c1",
                "path": "app/auth/security.py",
                "start_line": 20,
                "end_line": 35,
                "symbol_name": "create_access_token",
                "text": "def create_access_token():\n    return 'token'",
                "embed_text": "def create_access_token():\n    return 'token'",
            }
        ]

    srv.chunk_repo.get_by_ids = mock_get_by_ids
    srv.keyword_search.search = AsyncMock(return_value=[("c1", 1, 10.5)])
    srv.vector_search.search = AsyncMock(return_value=[("c1", 1, 0.88)])
    srv.symbol_lookup.lookup = AsyncMock(return_value=[])
    srv.summary_scope.get_summary_candidates = AsyncMock(return_value=[])
    return srv


@pytest.mark.asyncio
async def test_qa_graph_out_of_scope(mock_retrieval_service) -> None:
    settings = Settings(LLM_PROVIDER="fake")
    runner = QAGraphRunner(
        settings=settings,
        retrieval_service=mock_retrieval_service,
        llm_provider=FakeProvider(),
    )

    state: QAState = {
        "repo_id": "test_repo",
        "commit_sha": "abc1234",
        "user_id": "user1",
        "question": "Hello there, how is the weather?",
    }

    result = await runner.execute(state)
    assert result.get("route", {}).get("intent") == "out_of_scope"
    assert "assistant designed to explain" in result.get("answer", "")
    assert result.get("confidence", {}).get("label") == "N/A"


@pytest.mark.asyncio
async def test_qa_graph_full_execution(mock_retrieval_service) -> None:
    settings = Settings(LLM_PROVIDER="fake")
    runner = QAGraphRunner(
        settings=settings,
        retrieval_service=mock_retrieval_service,
        llm_provider=FakeProvider(),
    )

    state: QAState = {
        "repo_id": "test_repo",
        "commit_sha": "abc1234",
        "user_id": "user1",
        "question": "Where is create_access_token defined?",
    }

    result = await runner.execute(state)

    assert result.get("route", {}).get("intent") == "locate"
    assert len(result.get("candidates", [])) >= 1
    assert "S1" in result.get("context", "")
    assert "[S1]" in result.get("cleaned_answer", "")
    assert len(result.get("citations", [])) >= 1
    assert result.get("citations", [])[0]["source_id"] == "S1"
    assert result.get("confidence", {}).get("score", 0.0) > 0.0
    assert result.get("trace", {}).get("attempts") == 1
    assert "total" in result.get("timings", {})
