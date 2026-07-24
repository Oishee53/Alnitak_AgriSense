"""Application configuration, loaded from environment / .env.

Uses pydantic-settings so every value is typed and documented in one place.
Import the singleton `settings` anywhere: `from app.config import settings`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ — the anchor for every on-disk path below. Storage locations must NOT
# depend on the current working directory: launching uvicorn from the repo root
# instead of backend/ would otherwise silently create a SECOND, empty database
# and Chroma index, which looks exactly like "all my sessions and traces
# vanished". Anchoring here means the same data is found from anywhere.
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _anchor(path: str) -> str:
    """Resolve a possibly-relative path against backend/."""
    p = Path(path)
    return str(p if p.is_absolute() else (BACKEND_DIR / p).resolve())


class Settings(BaseSettings):
    # env_file must be an ABSOLUTE path for the same reason the storage paths
    # are anchored below: pydantic-settings resolves a relative env_file against
    # the current working directory, so starting the server from the repo root
    # instead of backend/ would silently load no .env at all — the app then
    # reports "OPENAI_API_KEY is not set" while the file is sitting right there.
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
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
    # Direct Debit endpoint per the official BDApps API Guide v1.1.3 §5.3
    # ("charges a specific amount from a subscriber's account").
    bdapps_caas_url: str = "https://developer.bdapps.com/caas/direct/debit"
    # SMS Send endpoint per §3.1 — used to deliver the paid weather/pest alert.
    bdapps_sms_url: str = "https://developer.bdapps.com/sms/send"
    bdapps_sandbox: bool = True
    # --- Live relay (to satisfy bdapps' originating-IP allowlist) ---
    # bdapps only accepts CaaS/SMS requests from a whitelisted host IP
    # (e.g. 103.108.140.219). When the backend runs elsewhere (a laptop),
    # point these at a thin PHP relay deployed ON that host: the backend POSTs
    # the transaction to the relay, and the relay makes the real bdapps call
    # from the allowed IP. Empty = call bdapps directly (only works when the
    # backend itself runs on the whitelisted host). See bdapps-relay/.
    bdapps_relay_url: str = ""      # e.g. https://103.108.140.219/agri/charge.php
    bdapps_sms_relay_url: str = ""  # e.g. https://103.108.140.219/agri/sms.php
    bdapps_relay_secret: str = ""   # shared secret the relay checks

    # --- App ---
    app_env: str = "development"
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:3000"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def model_post_init(self, __context) -> None:
        """Pin every storage path to backend/ so the data found is the same no
        matter which directory the process was started from."""
        object.__setattr__(self, "chroma_dir", _anchor(self.chroma_dir))
        object.__setattr__(self, "kb_dir", _anchor(self.kb_dir))

        # sqlite:///relative/path -> sqlite:////absolute/path
        url = self.database_url
        if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
            raw = url[len("sqlite:///") :]
            if raw and raw != ":memory:" and not Path(raw).is_absolute():
                object.__setattr__(
                    self, "database_url", "sqlite:///" + _anchor(raw).replace("\\", "/")
                )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
