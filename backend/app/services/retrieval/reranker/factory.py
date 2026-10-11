from __future__ import annotations

from app.core.config import Settings
from app.services.retrieval.reranker.base import RerankerProvider
from app.services.retrieval.reranker.fake import FakeRerankerProvider
from app.services.retrieval.reranker.fastembed_reranker import FastEmbedRerankerProvider

_reranker_instances: dict[str, RerankerProvider] = {}


def get_reranker_provider(settings: Settings) -> RerankerProvider:
    provider_name = settings.RERANKER_PROVIDER.lower().strip()
    key = f"{provider_name}:{settings.RERANKER_MODEL}"

    if key in _reranker_instances:
        return _reranker_instances[key]

    if provider_name == "fake":
        provider: RerankerProvider = FakeRerankerProvider()
    elif provider_name == "fastembed":
        provider = FastEmbedRerankerProvider(
            model_name=settings.RERANKER_MODEL,
            cache_dir=settings.MODEL_CACHE_DIR,
        )
    else:
        # Fallback to fake if unknown
        provider = FakeRerankerProvider()

    _reranker_instances[key] = provider
    return provider
