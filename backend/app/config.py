"""Application configuration, loaded from environment / .env.

Uses pydantic-settings so every value is typed and documented in one place.
Import the singleton `settings` anywhere: `from app.config import settings`.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM (OpenAI) ---
    openai_api_key: str = ""
    openai_base_url: str = ""  # optional override; blank = OpenAI default
    llm_model: str = "gpt-4o-mini"
    llm_max_tokens: int = 4096

    # --- Weather (Open-Meteo, keyless) ---
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_geocode_url: str = "https://geocoding-api.open-meteo.com/v1/search"

    # --- Storage ---
    database_url: str = "sqlite:///./data/agrisense.db"
    chroma_dir: str = "./data/chroma"
    kb_dir: str = "./data/knowledge_base"

    # --- bdapps CaaS ---
    bdapps_app_id: str = ""
    bdapps_app_password: str = ""
    bdapps_caas_url: str = "https://developer.bdapps.com/cass/send"
    bdapps_sandbox: bool = True

    # --- App ---
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
