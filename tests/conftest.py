"""Shared test fixtures.

Fixtures are either captured from public Banco Central market data or
generated synthetically. No test in this repository may use real
credentials, a real CPF or real personal financial information.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures"

FROZEN_NOW = datetime(2026, 9, 9, 15, 30, tzinfo=UTC)


@pytest.fixture
def load_fixture() -> Callable[[str], Any]:
    """Return a loader for a JSON fixture, relative to tests/fixtures."""

    def _load(relative_path: str) -> Any:
        return json.loads((FIXTURE_ROOT / relative_path).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def frozen_clock() -> Callable[[], datetime]:
    """A deterministic clock, so collected_at is assertable."""
    return lambda: FROZEN_NOW
