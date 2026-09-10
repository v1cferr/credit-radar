"""Application configuration, loaded from the environment.

Secrets are never hardcoded and never read from a committed file. The
database URL is wrapped in ``SecretStr`` because it carries a password, and
an accidental log line or traceback that prints the settings object must not
leak it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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

    cors_origins: str = "http://localhost:3007"
    """Comma-separated browser origins allowed to call this API.

    Kept narrow deliberately. This API serves personal credit data and has no
    reason to be reachable from an arbitrary page.
    """

    browser_profile_dir: Path = Path.home() / ".local/state/credit-radar/browser-profiles"
    """Where authenticated browser sessions are kept.

    Outside the repository, and outside the container. An authenticated
    session is a credential at least as strong as the password that produced
    it, and usually stronger, since it is already past the second factor.

    Under the user's state directory rather than anywhere shared, created
    with owner-only permissions.
    """

    chromium_path: str | None = None
    """Chromium for browser automation.

    Set from the development shell, because the binaries Playwright
    downloads are linked against paths that do not exist on NixOS. None means
    "let Playwright decide", which works on a conventional distribution.
    """

    http_timeout_seconds: float = Field(default=20.0, gt=0)
    """Mandatory outbound request timeout.

    Not a tuning knob. The Banco Central SGS API has been observed to hang
    indefinitely rather than return an error status for some invalid
    requests, so a request without a timeout can stall a collection run
    forever. See docs/providers/bcb-sgs.md.
    """

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read from the environment once."""
    return Settings()
