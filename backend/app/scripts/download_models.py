"""
Pre-downloads FastEmbed embedding and reranking models into the local cache directory (§16.4).
"""

from __future__ import annotations

import os
import sys

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    cache_dir = settings.MODEL_CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)
    print(f"Pre-downloading embedding and reranking models into: {cache_dir}")

    try:
        from fastembed import TextEmbedding

        print(f"Downloading embedding model ({settings.EMBEDDING_MODEL})...")
        _ = TextEmbedding(model_name=settings.EMBEDDING_MODEL, cache_dir=cache_dir)
        print("Embedding model cached successfully.")
    except Exception as exc:
        print(f"Warning: Could not pre-download FastEmbed model: {exc}", file=sys.stderr)

    try:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        print(f"Downloading reranker model ({settings.RERANKER_MODEL})...")
        _ = TextCrossEncoder(model_name=settings.RERANKER_MODEL, cache_dir=cache_dir)
        print("Reranker model cached successfully.")
    except Exception as exc:
        print(f"Notice: Reranker model download skipped or failed: {exc}", file=sys.stderr)

    print("Model pre-download complete.")


if __name__ == "__main__":
    main()
