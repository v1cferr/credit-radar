"""Application configuration, loaded from the environment.

Secrets are never hardcoded and never read from a committed file. The
database URL is wrapped in ``SecretStr`` because it carries a password, and
an accidental log line or traceback that prints the settings object must not
leak it.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for CreditRadar."""

    model_config = SettingsConfigDict(
        env_prefix="CREDIT_RADAR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://credit_radar:credit_radar@localhost:5434/credit_radar"
    )
    """Development default matches docker-compose.

    Port 5434 rather than 5432: this machine runs unrelated projects that
    already hold the conventional port. Override via the environment.
    """

    api_host: str = "127.0.0.1"
    """Loopback by default.

    This service handles credit and identity data and is private. Exposing it
    on a routable interface must be a deliberate, explicit change.
    """

    api_port: int = 8000
    log_level: str = "INFO"

    http_timeout_seconds: float = Field(default=20.0, gt=0)
    """Mandatory outbound request timeout.

    Not a tuning knob. The Banco Central SGS API has been observed to hang
    indefinitely rather than return an error status for some invalid
    requests, so a request without a timeout can stall a collection run
    forever. See docs/providers/bcb-sgs.md.
    """


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read from the environment once."""
    return Settings()
