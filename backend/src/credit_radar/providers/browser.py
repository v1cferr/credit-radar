"""Authenticated browser sessions.

Some sources have no API, no export and no downloadable report reachable
without a login. For those, a browser is the last integration tier, and the
session it produces has to be treated as what it is.

**An authenticated session is a credential, and a stronger one than the
password.** It is already past the second factor, so anyone holding it skips
the MFA that the password alone would still face. Everything here follows
from that: one isolated profile per source, owner-only permissions, outside
the repository, never in a container image, and never in a log.

**No security mechanism is bypassed.** CAPTCHA, MFA, gov.br confirmation and
device approval are completed by a person. The automation opens the page,
fills only what it is allowed to fill, and then stops and waits. There is no
code path here that attempts to solve or circumvent a challenge, and there
must not be one.

Requires the `rpa` extra:

    uv sync --extra rpa
"""

from __future__ import annotations

import logging
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from credit_radar.domain.provenance import SourceId

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.sync_api import BrowserContext

logger = logging.getLogger(__name__)

PROFILE_MODE = stat.S_IRWXU
"""0700. A session is a credential, so no group or other access."""


class BrowserUnavailableError(RuntimeError):
    """Playwright is not installed, or no usable browser was found."""


def profile_dir(source_id: SourceId, profile_root: Path) -> Path:
    """Return this source's profile directory, creating it owner-only.

    One directory per source, never shared. A single profile used for several
    bureaus would let a script that went wrong on one of them act with the
    session of another.
    """
    path = profile_root / source_id.value.replace(".", "_")
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(PROFILE_MODE)
    profile_root.chmod(PROFILE_MODE)
    return path


def has_session(source_id: SourceId, profile_root: Path) -> bool:
    """Whether a saved session exists for this source.

    Existence only. Whether it is still valid can only be known by using it,
    and a provider that finds it expired must ask for a new sign-in rather
    than trying to work around the challenge.
    """
    path = profile_root / source_id.value.replace(".", "_")
    return path.is_dir() and any(path.iterdir())


@contextmanager
def browser_session(
    source_id: SourceId,
    *,
    profile_root: Path,
    headed: bool,
    chromium_path: str | None = None,
    timeout_ms: int = 60_000,
) -> Iterator[BrowserContext]:
    """Open a persistent browser context for one source.

    A persistent user-data directory rather than a serialized cookie jar, on
    purpose: gov.br and the bureau portals remember a trusted device through
    more than cookies, and a profile that loses that state would force a
    fresh second factor on every run.

    Raises:
        BrowserUnavailableError: the `rpa` extra is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error:  # pragma: no cover - depends on the extra
        raise BrowserUnavailableError(
            "browser automation needs the 'rpa' extra: uv sync --extra rpa"
        ) from error

    directory = profile_dir(source_id, profile_root)

    launch_kwargs: dict[str, Any] = {
        "user_data_dir": str(directory),
        "headless": not headed,
        # A real locale and timezone: a Brazilian financial portal renders
        # dates and decimals according to them, and parsing would otherwise
        # depend on the machine's incidental settings.
        "locale": "pt-BR",
        "timezone_id": "America/Sao_Paulo",
        # Recording is off. A video or a trace of these pages would be a
        # credit report sitting on disk.
        "record_video_dir": None,
    }
    if chromium_path:
        launch_kwargs["executable_path"] = chromium_path

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(**launch_kwargs)
        context.set_default_timeout(timeout_ms)
        try:
            # Logged without the URL, which for an authenticated source can
            # carry an identifier in its query string.
            logger.info("Opened a browser session for %s", source_id.value)
            yield context
        finally:
            context.close()
