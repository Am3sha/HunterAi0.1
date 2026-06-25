"""Application configuration.

Settings are loaded from environment variables (prefix ``HUNTERAI_``) and an
optional ``.env`` file. Keeping configuration in one typed object means the rest
of the codebase never reads ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import make_url

# Repo-relative default for the managed tools directory:
# <repo>/.hunterai/tools  (this file lives at backend/app/core/config.py)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_TOOLS_DIR = _REPO_ROOT / ".hunterai" / "tools"


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="HUNTERAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "HunterAI"
    env: str = "development"
    debug: bool = True

    # --- API ---
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Managed tools ---
    tools_dir: Path = _DEFAULT_TOOLS_DIR

    # --- Database (used from Milestone 4) ---
    database_url: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        if value is None:
            return value
        if isinstance(value, str):
            # Require explicit psycopg v3 driver scheme for PostgreSQL.
            url = make_url(value)
            if url.drivername == "postgresql" and url.get_dialect().name == "postgresql":
                raise ValueError(
                    "HUNTERAI_DATABASE_URL must use postgresql+psycopg:// when targeting PostgreSQL with psycopg v3. "
                    "Use postgresql+psycopg://... instead of postgresql://..."
                )
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        """Allow a comma-separated string from the environment."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of truth)."""
    return Settings()
