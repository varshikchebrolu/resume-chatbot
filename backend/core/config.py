"""Central, environment-driven configuration for the Resume Toolkit backend.

All tunables live here so nothing is hardcoded across feature modules. Values are
read from environment variables (and backend/.env) via pydantic-settings.
"""
import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ root (this file lives in backend/core/).
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(BACKEND_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Credentials ---
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    # --- Models ---
    chat_model: str = Field(default="gemini-2.5-flash", alias="CHAT_MODEL")
    embedding_model: str = Field(
        default="gemini-embedding-001", alias="EMBEDDING_MODEL"
    )
    optimizer_model: str = Field(default="gemini-2.5-flash", alias="OPTIMIZER_MODEL")

    # --- App / server ---
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    # Comma-separated list of allowed CORS origins.
    cors_origins: str = Field(
        default="http://localhost:4001", alias="CORS_ORIGINS"
    )

    # --- Optimizer behavior ---
    acceptable_ats_score: int = Field(default=85, alias="ACCEPTABLE_ATS_SCORE")
    max_iterations: int = Field(default=4, alias="MAX_ITERATIONS")
    optimizer_timeout_seconds: int = Field(
        default=300, alias="OPTIMIZER_TIMEOUT_SECONDS"
    )

    # --- Input limits (characters) ---
    max_resume_chars: int = Field(default=30_000, alias="MAX_RESUME_CHARS")
    max_jd_chars: int = Field(default=20_000, alias="MAX_JD_CHARS")
    max_chat_chars: int = Field(default=8_000, alias="MAX_CHAT_CHARS")

    # --- Rate limits (requests per window, slowapi syntax) ---
    rate_limit_optimize: str = Field(default="5/minute", alias="RATE_LIMIT_OPTIMIZE")
    rate_limit_chat: str = Field(default="30/minute", alias="RATE_LIMIT_CHAT")

    # --- Postgres ---
    database_url: str = Field(default="", alias="DATABASE_URL")

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
