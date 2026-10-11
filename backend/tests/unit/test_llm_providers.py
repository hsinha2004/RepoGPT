import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.schemas.retrieval import RouteResult
from app.services.llm.base import ChatMessage
from app.services.llm.factory import get_llm_provider, resolve_model_name
from app.services.llm.fake import FakeProvider
from app.services.llm.pricing import calculate_cost
from app.services.llm.structured import parse_structured_response


class SampleSchema(BaseModel):
    name: str
    count: int


@pytest.mark.asyncio
async def test_fake_provider_complete_extractive_citations() -> None:
    provider = FakeProvider()
    messages = [
        ChatMessage(
            role="user",
            content="""<sources>
<source id="S1" path="backend/app/main.py" lines="10-25" symbol="create_app">
10 | def create_app():
11 |     app = FastAPI()
12 |     return app
</source>
<source id="S2" path="backend/app/auth.py" lines="5-15" symbol="login">
5 | def login(email: str):
6 |     return Token()
</source>
</sources>
Question: Where is create_app defined?""",
        )
    ]

    res = await provider.complete(messages)
    assert res.text
    assert "[S1]" in res.text
    assert "[S2]" in res.text
    assert "`create_app`" in res.text
    assert res.usage.prompt_tokens > 0
    assert res.usage.completion_tokens > 0
    assert res.finish_reason == "stop"


@pytest.mark.asyncio
async def test_fake_provider_complete_structured_route() -> None:
    provider = FakeProvider()
    messages = [
        ChatMessage(
            role="user",
            content="Where is the JWT token created in backend/app/auth/security.py?",
        )
    ]

    res = await provider.complete(messages, response_schema=RouteResult)
    assert res.parsed is not None
    assert isinstance(res.parsed, RouteResult)
    assert res.parsed.intent == "locate"
    assert res.parsed.strategy in ("keyword", "vector", "hybrid", "hybrid_rerank")


@pytest.mark.asyncio
async def test_fake_provider_stream() -> None:
    provider = FakeProvider()
    messages = [
        ChatMessage(
            role="user",
            content="""<sources>
<source id="S1" path="app/test.py" lines="1-2">
1 | print('hello')
</source>
</sources>
Question: Test question""",
        )
    ]

    tokens: list[str] = []
    final_usage = None
    async for delta in provider.stream(messages):
        if delta.text:
            tokens.append(delta.text)
        if delta.usage:
            final_usage = delta.usage

    full_text = "".join(tokens)
    assert "[S1]" in full_text
    assert final_usage is not None
    assert final_usage.completion_tokens > 0


def test_pricing_calculation() -> None:
    # Known model: gpt-4o ($2.50 / $10.00 per 1M)
    cost = calculate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
    assert cost is not None
    # 1000 * 2.5/1M + 500 * 10/1M = 0.0025 + 0.0050 = 0.0075
    assert cost == 0.0075

    # Fake / Ollama -> 0.0
    assert calculate_cost("fake", 5000, 2000) == 0.0
    assert calculate_cost("ollama-llama3", 5000, 2000) == 0.0

    # Unknown model -> None (never guessed)
    assert calculate_cost("my-custom-unlisted-model-v99", 100, 100) is None

    # Custom override JSON
    override = '{"custom-model": [1.0, 2.0]}'
    cost_override = calculate_cost(
        "custom-model",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        pricing_override_json=override,
    )
    assert cost_override == 3.0


def test_structured_json_extraction() -> None:
    raw_markdown = """Here is the result:
```json
{
  "name": "RepoGPT",
  "count": 42
}
```
Done."""
    parsed, err = parse_structured_response(raw_markdown, SampleSchema)
    assert err is None
    assert parsed is not None
    assert parsed.name == "RepoGPT"
    assert parsed.count == 42


def test_factory_offline_mode() -> None:
    settings = Settings(LLM_PROVIDER="gemini", LLM_API_KEY=None)
    provider = get_llm_provider(settings)
    assert provider.name == "fake"
    assert isinstance(provider, FakeProvider)

    # Model resolution
    assert resolve_model_name(settings, fast=False) == "gemini-2.0-flash"
    assert resolve_model_name(settings, fast=True) == "gemini-1.5-flash"
