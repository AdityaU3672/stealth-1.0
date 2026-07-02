from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PORT: int = 3002
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ingestion_service"
    DB_POOL_SIZE: int = 2
    DB_MAX_OVERFLOW: int = 2
    JWT_SECRET: str = "change_me"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    LLM_PROVIDER: str = "claude"  # "claude" or "openai"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5"
    ANTHROPIC_PR_MODEL: str = "claude-haiku-4-5"
    ANTHROPIC_PR_FAST_MODE: bool = False
    ANTHROPIC_PR_FAST_MODE_BETA: str = "fast-mode-2026-02-01"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_PR_MAX_TOKENS: int = 2048

    RAG_TOP_K_DEFAULT: int = 6
    RAG_TOP_K_REDUCED: int = 4
    RAG_MAX_CHARS_PER_CHUNK: int = 1200
    RAG_MAX_TOTAL_CHARS: int = 6000

    INDEX_WAIT_TIMEOUT_SECONDS: float = 30.0

    WEBHOOK_BASE_URL: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    EMBEDDING_PROVIDER: str = "voyage"  # "voyage" or "openai"
    EMBEDDING_DIMENSION: int = 1536
    VOYAGE_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
