from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise Support Agent"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/enterprise_support_agent"
    frontend_origin: str = "http://localhost:3000"

    jwt_secret_key: str = "replace-with-dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    llm_provider: str = "openai"
    openai_api_key: str = "replace-with-your-key"
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"
    llm_timeout_seconds: int = Field(default=30, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)
    llm_enable_thinking: Optional[bool] = None
    llm_enabled: bool = False

    storage_dir: str = "app/storage"
    chunk_size: int = 800
    chunk_overlap: int = 120
    rag_top_k: int = 5
    rag_similarity_threshold: float = Field(default=0.75, ge=0, le=1)
    rag_candidate_k: int = Field(default=30, ge=5, le=200)
    rag_rrf_k: int = Field(default=60, ge=1, le=500)
    rag_lexical_min_score: float = Field(default=0.05, ge=0, le=1)
    rag_max_chunks_per_document: int = Field(default=3, ge=1, le=20)
    rag_context_token_budget: int = Field(default=3000, ge=200, le=30000)
    rag_mmr_lambda: float = Field(default=0.75, ge=0, le=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
