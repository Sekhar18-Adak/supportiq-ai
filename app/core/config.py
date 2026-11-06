from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):

    app_name: str = "SupportIQ AI"
    app_env: str = "development"

    # API Keys
    openrouter_api_key: str = ""
    tavily_api_key: str = ""
    pinecone_api_key: str = ""

    # Pinecone
    pinecone_index_name: str = "supportiq-embedding-1536"
    pinecone_namespace: str = "company-it-kb"

    # Models
    embedding_model: str = "openai/text-embedding-3-small"
    openrouter_model: str = "recursive/flint-v1.0:free"

    # OpenRouter
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # RAG Configuration
    top_k: int = 4
    max_retries: int = 1

    # Security
    admin_api_key: str = "change-me"

    # Directories
    audit_db_path: str = str(BASE_DIR / "data" / "audit.db")
    upload_dir: str = str(BASE_DIR / "uploads")
    sample_kb_dir: str = str(BASE_DIR / "data" / "sample_kb")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()