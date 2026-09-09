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


@pytest.fixture(scope="session")
def database_url() -> str:
    """URL of a PostgreSQL instance for integration tests.

    Integration tests run against a real PostgreSQL because the behaviours
    they cover -- unconstrained numeric scale, ON CONFLICT deduplication,
    DISTINCT ON -- are properties of PostgreSQL, not of SQLAlchemy. Verifying
    them against SQLite would prove nothing about production.
    """
    import os

    return os.environ.get(
        "CREDIT_RADAR_TEST_DATABASE_URL",
        "postgresql+psycopg://credit_radar:credit_radar@localhost:5434/credit_radar_test",
    )


@pytest.fixture(scope="session")
def engine(database_url: str):
    """Create the test database schema, or skip if PostgreSQL is unavailable."""
    import sqlalchemy
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    from credit_radar.persistence.models import Base

    url = make_url(database_url)
    admin_url = url.set(database="postgres")

    try:
        admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
        admin.dispose()
    except sqlalchemy.exc.OperationalError as error:
        pytest.skip(f"PostgreSQL is not reachable for integration tests: {error}")

    test_engine = create_engine(database_url)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine):
    """A session rolled back after each test, so cases stay isolated."""
    from sqlalchemy.orm import Session

    from credit_radar.persistence.models import Base

    with Session(engine, expire_on_commit=False) as db_session:
        yield db_session
        db_session.rollback()

    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
