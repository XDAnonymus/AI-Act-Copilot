from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    llm_model: str = "qwen3.8:latest"
    embedding_model: str = "embeddinggemma:latest"
    ollama_base_url: str = "http://localhost:11434"

    qdrant_path: str = str(BASE_DIR / "data" / "qdrant")
    qdrant_collection: str = "eu_ai_act"
    embedding_dimensions: int = 768

    retrieval_top_k: int = 8
    max_evidence: int = 8
    max_research_tasks: int = 3
    max_retries: int = 1

    data_dir: str = str(BASE_DIR / "data")
    sources_file: str = str(BASE_DIR / "data" / "sources.yaml")
    date_rules_file: str = str(BASE_DIR / "data" / "rules" / "effective_dates.yaml")


settings = Settings()
