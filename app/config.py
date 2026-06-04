"""Application configuration via environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ai-upgrade-recommendation-engine"
    environment: str = "local"

    # Database
    database_url: str = "sqlite:///./recommendations.db"

    # OpenAI (optional — the engine degrades to deterministic explanations without it)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_enabled: bool = True

    # Risk thresholds that gate human review
    human_review_risk_threshold: float = 0.6
    high_criticality_requires_review: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
