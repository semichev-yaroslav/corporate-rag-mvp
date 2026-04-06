from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    app_name: str = Field(default="Локальный RAG по документам", alias="APP_NAME")
    environment: str = Field(default="development", alias="APP_ENVIRONMENT")
    host: str = Field(default="127.0.0.1", alias="APP_HOST")
    port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+asyncpg://rag_user:rag_password@localhost:5432/corporate_rag",
        alias="APP_DATABASE_URL",
    )
    documents_dir: str = Field(default="./documents", alias="APP_DOCUMENTS_DIR")
    auto_apply_db_migrations: bool = Field(default=False, alias="APP_AUTO_APPLY_DB_MIGRATIONS")

    embedding_service_url: str = Field(default="http://127.0.0.1:8010", alias="APP_EMBEDDING_SERVICE_URL")
    openai_api_key: str | None = Field(default=None, alias="APP_OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="APP_OPENAI_MODEL")

    telegram_bot_token: str | None = Field(default=None, alias="APP_TELEGRAM_BOT_TOKEN")
    allowed_telegram_user_ids: list[str] = Field(default_factory=list, alias="APP_ALLOWED_TELEGRAM_USER_IDS")
    operator_telegram_user_ids: list[str] = Field(
        default_factory=list,
        alias="APP_OPERATOR_TELEGRAM_USER_IDS",
    )
    require_allowlist: bool = Field(default=True, alias="APP_REQUIRE_ALLOWLIST")
    api_base_url: str = Field(default="http://127.0.0.1:8000", alias="APP_API_BASE_URL")

    retrieval_top_k: int = Field(default=8, alias="APP_RETRIEVAL_TOP_K")
    retrieval_max_documents: int = Field(default=3, alias="APP_RETRIEVAL_MAX_DOCUMENTS")
    retrieval_min_confidence: float = Field(default=0.25, alias="APP_RETRIEVAL_MIN_CONFIDENCE")
    conversation_history_messages: int = Field(default=10, alias="APP_CONVERSATION_HISTORY_MESSAGES")

    embedding_model_id: str = Field(
        default="ai-sage/Giga-Embeddings-instruct",
        alias="EMBEDDER_MODEL_ID",
    )
    embedding_quantization: str = Field(default="4bit", alias="EMBEDDER_QUANTIZATION")
    embedding_dimensions: int = Field(default=2048, alias="EMBEDDER_DIMENSIONS")
    embedding_device: str = Field(default="cuda", alias="EMBEDDER_DEVICE")
    embedder_host: str = Field(default="127.0.0.1", alias="EMBEDDER_HOST")
    embedder_port: int = Field(default=8010, alias="EMBEDDER_PORT")
    embedder_allow_cpu_fallback: bool = Field(default=True, alias="EMBEDDER_ALLOW_CPU_FALLBACK")

    @field_validator("allowed_telegram_user_ids", "operator_telegram_user_ids", mode="before")
    @classmethod
    def parse_csv_list(cls, value: str | int | list[str] | list[int] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        normalized = str(value).strip()
        return [normalized] if normalized else []


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
