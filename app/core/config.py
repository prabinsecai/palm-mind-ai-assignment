from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Palm Mind AI Hiring Assignment"
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = Field(..., alias="DATABASE_URL")

    redis_url: str = "redis://localhost:6379/0"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "palm_mind_documents"

    openai_api_key: str = ""
    openai_base_url: str = "https://openrouter.ai/api/v1"
    openai_chat_model: str = "liquid/lfm-2.5-2.6b:free"
    openai_embedding_model: str = "liquid/lfm-2.5-embedding-350m:free"
    embedding_dimensions: int = 1024

    rag_top_k: int = 5
    chat_memory_ttl_seconds: int = 86400
    max_upload_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()