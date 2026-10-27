"""PaperMind configuration via pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────
    app_name: str = "PaperMind"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://papermind:papermind@localhost:5432/papermind"
    database_url_sync: str = "postgresql://papermind:papermind@localhost:5432/papermind"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Celery ───────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Groq API ─────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"

    # ── Agent (LangGraph) ────────────────────────────────────
    agent_model_name: str = "qwen/qwen3.8-27b"  # needs reliable tool-calling
    agent_max_iterations: int = 5

    # ── Semantic Scholar ─────────────────────────────────────
    semantic_scholar_api_key: str = ""  # Optional — works without key
    semantic_scholar_base_url: str = "https://api.semanticscholar.org/graph/v1"

    # ── Embedding Model ──────────────────────────────────────
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # ── Search ───────────────────────────────────────────────
    default_search_limit: int = 10
    max_papers_per_topic: int = 500

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://papermind.vercel.app",
        "https://papermind-ankit.vercel.app",
    ]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
