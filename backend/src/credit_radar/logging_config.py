"""Logging setup, and the loggers this project deliberately silences.

Configured in one place because the decision below is a privacy control, not
a formatting preference, and it must not depend on which entry point started
the process.
"""

from __future__ import annotations

import logging

NOISY_LOGGERS: tuple[str, ...] = ("httpx", "httpcore")
"""HTTP client loggers pinned to WARNING.

Two reasons, and the second is the one that matters.

The first is that they log one INFO line per request, which defeats the
collector's quiet mode: a scheduled run on a day when nothing changed is
supposed to leave NOTHING in the journal, so that silence is informative and
a real failure stands out. Seven "same as yesterday" lines a day is a journal
nobody reads.

The second is that httpx logs the full request URL. For public Banco Central
series that is harmless. For the authenticated providers coming later it is
not: a bureau or SCR endpoint can carry a CPF or an account identifier in the
query string, and a journal is exactly the kind of place personal data ends
up by accident and stays for months. Redacting per call site would mean
getting it right every time; silencing the logger is the version that cannot
be forgotten.

Warnings and errors still come through, so a failing request is never hidden.
"""


def configure_logging(level: str) -> None:
    """Configure logging for a process entry point."""
    logging.basicConfig(
        level=level.upper(),
        format="%(levelname)s %(name)s: %(message)s",
    )
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
