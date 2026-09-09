"""Shared HTTP access for providers.

Wraps httpx to guarantee the properties every provider needs, so that no
individual provider has to remember them: a mandatory timeout, bounded
retries for transient failures, and a failure taxonomy instead of raw
transport exceptions.

Response bodies are never logged. Public market data is harmless, but this
same client will later carry authenticated credit-bureau responses
containing CPF, debts and account data, and a logging habit established now
is the one that will still be in place then.
"""

from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import Any, Self

import httpx

from credit_radar.providers.errors import (
    ProviderNoDataError,
    ProviderResponseInvalidError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class HttpClient:
    """A synchronous JSON HTTP client with a mandatory timeout.

    Synchronous by deliberate choice. CreditRadar is a single-user system
    with no concurrency pressure, and a sync stack keeps tests, migrations
    and request handling simple. Concurrency, if it is ever needed, belongs
    at the ingestion-scheduling level rather than spread through every layer.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_attempts: int = 2,
        backoff_seconds: float = 1.0,
        user_agent: str = "credit-radar/0.1 (personal use)",
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds
        self._client = httpx.Client(
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            follow_redirects=True,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_json(self, url: str, *, params: dict[str, str] | None = None) -> Any:
        """Fetch and decode a JSON document.

        Retries only failures that may plausibly succeed on a second attempt.
        ``max_attempts`` is intentionally small: when a source hangs until the
        timeout, every retry costs the full timeout, and a hang is at least as
        likely to signal a permanently malformed request as a transient fault.

        Raises:
            ProviderNoDataError: the source reported nothing for this request (404).
            ProviderUnavailableError: transport failure, timeout or server error.
            ProviderResponseInvalidError: the body was not valid JSON.
        """
        last_error: Exception | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.get(url, params=params)
            except httpx.TimeoutException:
                last_error = ProviderUnavailableError(f"request to {url} timed out")
                logger.warning("Timeout fetching %s (attempt %d)", url, attempt)
            except httpx.HTTPError as error:
                last_error = ProviderUnavailableError(f"transport error requesting {url}: {error}")
                logger.warning("Transport error fetching %s (attempt %d)", url, attempt)
            else:
                if response.status_code == httpx.codes.NOT_FOUND:
                    # An empty result, not a fault: several data APIs -- the
                    # BCB SGS API among them -- answer a valid query with no
                    # matching rows using 404 rather than an empty array.
                    raise ProviderNoDataError(f"source reported no data for {url}")

                if response.status_code in RETRYABLE_STATUS:
                    last_error = ProviderUnavailableError(
                        f"source returned {response.status_code} for {url}"
                    )
                    logger.warning(
                        "Retryable status %d fetching %s (attempt %d)",
                        response.status_code,
                        url,
                        attempt,
                    )
                else:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as error:
                        raise ProviderUnavailableError(
                            f"source returned {response.status_code} for {url}"
                        ) from error

                    try:
                        return response.json()
                    except ValueError as error:
                        # Body deliberately omitted from the message: it may
                        # carry personal data for authenticated providers.
                        raise ProviderResponseInvalidError(
                            f"response from {url} was not valid JSON"
                        ) from error

            if attempt < self._max_attempts:
                time.sleep(self._backoff_seconds * attempt)

        assert last_error is not None  # every failing branch above assigns it
        raise last_error
