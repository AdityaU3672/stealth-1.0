from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PORT: int = 3001
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ingestion_service"
    DB_POOL_SIZE: int = 2
    DB_MAX_OVERFLOW: int = 2
    JWT_SECRET: str = "change_me"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "ingestion-artifacts"

    ASSEMBLYAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_SIGNAL_MODEL: str = "claude-haiku-4-5"
    ANTHROPIC_SIGNAL_EFFORT: str = "low"
    ANTHROPIC_SYNTHESIS_MODEL: str = "claude-haiku-4-5"
    ANTHROPIC_SYNTHESIS_EFFORT: str = "medium"
    ANTHROPIC_SYNTHESIS_RETRY_MODEL: str = "claude-haiku-4-5"
    ANTHROPIC_SYNTHESIS_RETRY_EFFORT: str = "medium"
    ANTHROPIC_ENABLE_PROMPT_CACHING: bool = True

    EMBEDDING_PROVIDER: str = "voyage"
    EMBEDDING_DIMENSION: int = 1536
    VOYAGE_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    SYNTHESIS_CLUSTER_THRESHOLD: float = 0.75
    SYNTHESIS_FR_DEDUP_THRESHOLD: float = 0.82
    SYNTHESIS_MAX_SIGNALS: int = 2000
    SYNTHESIS_AUTO_TRIGGER_MIN: int = 5
    SYNTHESIS_CLUSTER_CONCURRENCY: int = 4
    SYNTHESIS_RETRY_CONFIDENCE_THRESHOLD: float = 0.65
    SYNTHESIS_HIGH_VALUE_SIGNAL_COUNT: int = 6
    SYNTHESIS_MAX_REPRESENTATIVE_SIGNALS: int = 5
    SYNTHESIS_STALE_RUN_GRACE_SECONDS: int = 45
    INGESTION_BATCH_CONCURRENCY: int = 5
    TRIGGER_RUNTIME_ENABLED: bool = False

    SLACK_CLIENT_ID: str | None = None
    SLACK_CLIENT_SECRET: str | None = None
    MICROSOFT_CLIENT_ID: str | None = None
    MICROSOFT_CLIENT_SECRET: str | None = None
    MICROSOFT_TENANT_ID: str | None = None
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    ZENDESK_CLIENT_ID: str | None = None
    ZENDESK_CLIENT_SECRET: str | None = None
    FIGMA_CLIENT_ID: str | None = None
    FIGMA_CLIENT_SECRET: str | None = None
    INTERCOM_CLIENT_ID: str | None = None
    INTERCOM_CLIENT_SECRET: str | None = None
    SERVICENOW_CLIENT_ID: str | None = None
    SERVICENOW_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    CREDENTIALS_ENCRYPTION_KEY: str = Field(default="")

    # Agent service (code / PR jobs). Same JWT as synthesis; leave empty to skip agent-backed fields in chat tools.
    AGENT_SERVICE_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("EMBEDDING_PROVIDER")
    @classmethod
    def validate_embedding_provider(cls, value: str) -> str:
        if value not in {"voyage", "openai"}:
            raise ValueError("EMBEDDING_PROVIDER must be 'voyage' or 'openai'")
        return value

    @field_validator("EMBEDDING_DIMENSION")
    @classmethod
    def validate_embedding_dimension(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("EMBEDDING_DIMENSION must be greater than 0")
        return value

    @field_validator(
        "ANTHROPIC_SIGNAL_EFFORT",
        "ANTHROPIC_SYNTHESIS_EFFORT",
        "ANTHROPIC_SYNTHESIS_RETRY_EFFORT",
    )
    @classmethod
    def validate_effort(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"low", "medium", "high"}:
            raise ValueError("Anthropic effort must be one of: low, medium, high")
        return normalized

    @field_validator(
        "SYNTHESIS_CLUSTER_CONCURRENCY",
        "SYNTHESIS_HIGH_VALUE_SIGNAL_COUNT",
        "SYNTHESIS_MAX_REPRESENTATIVE_SIGNALS",
        "SYNTHESIS_STALE_RUN_GRACE_SECONDS",
        "INGESTION_BATCH_CONCURRENCY",
        "DB_POOL_SIZE",
    )
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be greater than 0")
        return value

    @field_validator("DB_MAX_OVERFLOW")
    @classmethod
    def validate_non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Value must be greater than or equal to 0")
        return value

    @field_validator("SYNTHESIS_RETRY_CONFIDENCE_THRESHOLD")
    @classmethod
    def validate_retry_threshold(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("SYNTHESIS_RETRY_CONFIDENCE_THRESHOLD must be between 0 and 1")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
