"""
Application Configuration and Settings (Pydantic Settings)
"""

from functools import lru_cache
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def clean_env_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                if isinstance(v, str):
                    val = v.strip()
                    # Strip inline comments (e.g. "value # comment" or " # comment")
                    if " #" in val:
                        val = val.split(" #", 1)[0].strip()
                    if val.startswith("#") or val == "":
                        # Omit empty or pure comment values so Pydantic defaults apply
                        continue
                    cleaned[k] = val
                else:
                    cleaned[k] = v
            return cleaned
        return data

    # ---------- General ----------
    ENVIRONMENT: str = Field(default="development")
    APP_NAME: str = Field(default="RepoGPT")
    APP_BASE_URL: str = Field(default="http://localhost:5173")
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="console")
    CORS_ORIGINS: str = Field(default="http://localhost:5173")
    ALLOW_REGISTRATION: bool = Field(default=True)
    FEATURE_PR_REVIEW: bool = Field(default=True)
    FEATURE_GITHUB_OAUTH: bool = Field(default=False)
    EXPOSE_API_DOCS: bool = Field(default=True)

    # ---------- Security ----------
    JWT_SECRET: str = Field(
        default="default-dev-secret-key-must-be-replaced-with-64-random-bytes-in-prod-environment"
    )
    JWT_ACCESS_TTL_MINUTES: int = Field(default=15)
    REFRESH_TTL_DAYS: int = Field(default=7)
    ENCRYPTION_KEY: str = Field(default="MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE=")
    COOKIE_SECURE: bool = Field(default=False)
    ADMIN_EMAIL: str = Field(default="admin@repogpt.local")
    ADMIN_PASSWORD: str = Field(default="AdminPassword123!")

    # ---------- MongoDB ----------
    MONGO_ROOT_USER: str = Field(default="root")
    MONGO_ROOT_PASSWORD: str = Field(default="rootpassword")
    MONGO_APP_USER: str = Field(default="repogpt")
    MONGO_APP_PASSWORD: str = Field(default="apppassword")
    MONGO_HOST: str = Field(default="localhost")
    MONGO_PORT: int = Field(default=27017)
    MONGODB_DB: str = Field(default="repogpt")
    MONGODB_URI: str | None = Field(default=None)

    # ---------- Redis ----------
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="")
    REDIS_URL: str | None = Field(default=None)

    # ---------- Vector store ----------
    VECTOR_STORE: str = Field(default="chroma")
    CHROMA_HOST: str = Field(default="localhost")
    CHROMA_PORT: int = Field(default=8000)

    # ---------- Storage ----------
    DATA_DIR: str = Field(default="./data")
    MODEL_CACHE_DIR: str = Field(default="./models")

    # ---------- Ingestion limits ----------
    MAX_REPO_SIZE_MB: int = Field(default=300)
    MAX_DOWNLOAD_SIZE_MB: int = Field(default=300)
    MAX_UPLOAD_SIZE_MB: int = Field(default=100)
    MAX_UNCOMPRESSED_SIZE_MB: int = Field(default=600)
    MAX_ARCHIVE_ENTRIES: int = Field(default=30000)
    MAX_FILES: int = Field(default=8000)
    MAX_FILE_SIZE_KB: int = Field(default=1024)
    MAX_CHUNKS_PER_REPO: int = Field(default=60000)

    # ---------- GitHub ----------
    GITHUB_API_URL: str = Field(default="https://api.github.com")
    GITHUB_TOKEN: str | None = Field(default=None)
    GITHUB_OAUTH_CLIENT_ID: str | None = Field(default=None)
    GITHUB_OAUTH_CLIENT_SECRET: str | None = Field(default=None)
    GITHUB_WEBHOOK_SECRET: str = Field(default="webhooksecret")

    # ---------- LLM ----------
    LLM_PROVIDER: str = Field(default="gemini")
    LLM_API_KEY: str | None = Field(default=None)
    LLM_BASE_URL: str | None = Field(default=None)
    LLM_MODEL: str | None = Field(default=None)
    LLM_FAST_MODEL: str | None = Field(default=None)
    LLM_TEMPERATURE: float = Field(default=0.1)
    LLM_MAX_OUTPUT_TOKENS: int = Field(default=1500)
    LLM_TIMEOUT_SECONDS: int = Field(default=90)
    LLM_MAX_RPM: int = Field(default=10)
    LLM_MAX_CONCURRENCY: int = Field(default=4)
    LLM_PRICING_JSON: str | None = Field(default=None)

    # ---------- Embeddings & reranking ----------
    EMBEDDING_PROVIDER: str = Field(default="fastembed")
    EMBEDDING_MODEL: str = Field(default="jinaai/jina-embeddings-v2-base-code")
    EMBEDDING_API_KEY: str | None = Field(default=None)
    EMBEDDING_BATCH_SIZE: int = Field(default=32)
    RERANKER_PROVIDER: str = Field(default="fastembed")
    RERANKER_MODEL: str = Field(default="Xenova/ms-marco-MiniLM-L-6-v2")

    # ---------- Retrieval ----------
    RETRIEVAL_CANDIDATES: int = Field(default=50)
    RERANK_TOP_N: int = Field(default=30)
    CONTEXT_TOP_K: int = Field(default=8)
    CONTEXT_MAX_TOKENS: int = Field(default=6000)
    RRF_K: int = Field(default=60)
    MIN_EVIDENCE_SCORE: float = Field(default=0.30)
    MAX_RETRIEVAL_ATTEMPTS: int = Field(default=2)
    ROUTER_MODE: str = Field(default="hybrid")
    ENABLE_GROUNDING_CHECK: bool = Field(default=True)
    ENABLE_LLM_SUMMARIES: bool = Field(default=False)
    LLM_SUMMARY_MAX_FILES: int = Field(default=40)
    ANSWER_CACHE_TTL_SECONDS: int = Field(default=86400)
    BM25_LRU_CACHE_SIZE: int = Field(default=10)

    # ---------- Quotas & rate limits ----------
    DEFAULT_QUOTA_QUESTIONS_PER_DAY: int = Field(default=200)
    DEFAULT_QUOTA_INGESTIONS_PER_DAY: int = Field(default=10)
    DEFAULT_QUOTA_REVIEWS_PER_DAY: int = Field(default=20)
    DEFAULT_QUOTA_TOKENS_PER_DAY: int = Field(default=1000000)
    RATE_LIMIT_PER_MINUTE: int = Field(default=120)
    RATE_LIMIT_AUTH_PER_MINUTE: int = Field(default=10)
    RATE_LIMIT_CHAT_PER_MINUTE: int = Field(default=20)

    # ---------- Processes ----------
    API_WORKERS: int = Field(default=1)
    CELERY_CONCURRENCY: int = Field(default=2)

    # ---------- Phase 2 ----------
    ENABLE_STATIC_ANALYSIS: bool = Field(default=True)
    REVIEW_MAX_FILES: int = Field(default=50)
    REVIEW_MAX_DIFF_LINES: int = Field(default=3000)
    REVIEW_MIN_CONFIDENCE: float = Field(default=0.5)

    # ---------- Production ----------
    DOMAIN: str | None = Field(default=None)
    ACME_EMAIL: str | None = Field(default=None)
    IMAGE_TAG: str | None = Field(default=None)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def get_mongodb_uri(self) -> str:
        if self.MONGODB_URI and self.MONGODB_URI.strip() and not self.MONGODB_URI.strip().startswith("#"):
            return self.MONGODB_URI.strip()
        if self.MONGO_APP_USER and self.MONGO_APP_PASSWORD:
            return (
                f"mongodb://{self.MONGO_APP_USER}:{self.MONGO_APP_PASSWORD}"
                f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGODB_DB}?authSource={self.MONGODB_DB}"
            )
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGODB_DB}"

    def get_redis_url(self, db: int = 0) -> str:
        if self.REDIS_URL and self.REDIS_URL.strip() and not self.REDIS_URL.strip().startswith("#"):
            # If explicit URL provided, swap db index if requested
            base = self.REDIS_URL.strip().rstrip("/0123456789")
            return f"{base}/{db}"
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{db}"


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
