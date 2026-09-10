"""Prepare the end-to-end database with deterministic synthetic data.

Creates the database if needed, applies migrations, wipes what is there and
inserts a fixed dataset shaped to exercise every UI state the dashboard can
show. Run by Playwright's global setup; safe to run by hand.

ALL DATA HERE IS SYNTHETIC. The values are deliberately different from the
real Banco Central figures so that an E2E screenshot can never be mistaken
for a real reading of the credit market.

The database name is checked before anything is written. This script
truncates tables, and the whole point of a separate E2E database is that a
mistake cannot reach the personal one, so that has to be enforced rather than
remembered.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import NoReturn

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

REQUIRED_NAME_MARKERS = ("e2e", "test")
"""The database name must contain one of these.

A guard and not a convention: this script deletes rows, so pointing it at
`credit_radar` would wipe the real historical series, which is the one asset
in this project that cannot be rebuilt.
"""

COLLECTOR = "tests.e2e.seed"
COLLECTOR_VERSION = "e2e-1"
SOURCE_ID = "bcb.sgs"

# A fixed anchor, so every reference date and charted value is identical on
# every run. Collection timestamps stay relative to now, because freshness is
# what the staleness states depend on.
ANCHOR = date(2026, 8, 30)


# NoReturn so callers do not need an unreachable return after it, and so a
# type checker knows the guard actually stops execution.
def _fail(message: str) -> NoReturn:
    print(f"seed_e2e: {message}", file=sys.stderr)
    raise SystemExit(1)


def _guard(database_url: str) -> str:
    url = make_url(database_url)
    name = url.database or ""
    if not any(marker in name for marker in REQUIRED_NAME_MARKERS):
        _fail(
            f"refusing to seed database {name!r}: the name must contain one of "
            f"{REQUIRED_NAME_MARKERS}. This script truncates tables, and the "
            f"personal database must be unreachable from it."
        )
    return name


def _ensure_database(database_url: str) -> None:
    url = make_url(database_url)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
            print(f"seed_e2e: created database {url.database}")
    admin.dispose()


def _migrate() -> None:
    # Runs the real migrations rather than metadata.create_all, so E2E
    # exercises the schema the deployment actually gets, including the
    # constraints the dedup behaviour depends on.
    config = Config("alembic.ini")
    command.upgrade(config, "head")


def _observation(
    *,
    indicator: str,
    reference_date: date,
    value: str,
    unit: str,
    series: str,
    collected_at: datetime,
) -> dict[str, object]:
    return {
        "indicator_code": indicator,
        "reference_date": reference_date,
        "value": Decimal(value),
        "unit": unit,
        "source_id": SOURCE_ID,
        "source_reference": f"bcdata.sgs.{series}",
        "collector": COLLECTOR,
        "collector_version": COLLECTOR_VERSION,
        "collected_at": collected_at,
        "request_url": None,
    }


def _run(
    *,
    series: str,
    status: str,
    observation_count: int,
    finished_at: datetime,
    error_message: str | None = None,
) -> dict[str, object]:
    return {
        "source_id": SOURCE_ID,
        "source_reference": f"bcdata.sgs.{series}",
        "collector": COLLECTOR,
        "collector_version": COLLECTOR_VERSION,
        "started_at": finished_at - timedelta(seconds=4),
        "finished_at": finished_at,
        "status": status,
        "observation_count": observation_count,
        "error_message": error_message,
    }


def build_dataset(now: datetime) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Return the observations and runs to insert.

    Shaped so that one seeded database exercises every state a card can be
    in, which is what lets the UI-state assertions be deterministic instead
    of depending on which day the suite runs.
    """
    fresh = now - timedelta(minutes=5)
    stale = now - timedelta(days=10)

    observations: list[dict[str, object]] = []

    # SELIC_TARGET: a healthy daily series with enough points to chart.
    # A step change part-way through, because a flat line would not prove the
    # chart is plotting the data rather than a constant.
    for offset in range(30):
        reference = ANCHOR - timedelta(days=29 - offset)
        value = "12.75" if offset < 18 else "13.25"
        observations.append(
            _observation(
                indicator="SELIC_TARGET",
                reference_date=reference,
                value=value,
                unit="percent_per_year",
                series="432",
                collected_at=fresh,
            )
        )

    # VEHICLE_FINANCING_RATE_PF: a healthy monthly series.
    for index, value in enumerate(["23.10", "23.80", "24.50"]):
        observations.append(
            _observation(
                indicator="VEHICLE_FINANCING_RATE_PF",
                reference_date=date(2026, 6 + index, 1),
                value=value,
                unit="percent_per_year",
                series="20749",
                collected_at=fresh,
            )
        )

    # The two mortgage regimes, far enough apart that a test can prove the UI
    # keeps them distinct rather than collapsing them.
    observations.append(
        _observation(
            indicator="MORTGAGE_RATE_MARKET_PF",
            reference_date=date(2026, 8, 1),
            value="15.75",
            unit="percent_per_year",
            series="20772",
            collected_at=fresh,
        )
    )
    observations.append(
        _observation(
            indicator="MORTGAGE_RATE_REGULATED_PF",
            reference_date=date(2026, 8, 1),
            value="9.80",
            unit="percent_per_year",
            series="20773",
            collected_at=fresh,
        )
    )

    # IPCA_MONTHLY: has a value, but its last collection is old. The card
    # must say so instead of presenting it as current.
    observations.append(
        _observation(
            indicator="IPCA_MONTHLY",
            reference_date=date(2026, 7, 1),
            value="0.42",
            unit="percent_per_month",
            series="433",
            collected_at=stale,
        )
    )

    # SELIC_ANNUALIZED: has an older value AND a failed last collection. The
    # card must warn rather than show the number as if it were current.
    observations.append(
        _observation(
            indicator="SELIC_ANNUALIZED",
            reference_date=date(2026, 8, 28),
            value="12.60",
            unit="percent_per_year",
            series="1178",
            collected_at=stale,
        )
    )

    # IGPM_MONTHLY is intentionally absent: no observations and no run at
    # all, so the empty state and "never collected" are exercised too.

    runs: list[dict[str, object]] = [
        _run(series="432", status="success", observation_count=30, finished_at=fresh),
        _run(series="20749", status="success", observation_count=3, finished_at=fresh),
        _run(series="20772", status="success", observation_count=1, finished_at=fresh),
        _run(series="20773", status="success", observation_count=1, finished_at=fresh),
        _run(series="433", status="success", observation_count=1, finished_at=stale),
        _run(
            series="1178",
            status="failed",
            observation_count=0,
            finished_at=fresh,
            error_message="source returned 503 (synthetic, seeded for E2E)",
        ),
    ]

    return observations, runs


def main() -> int:
    database_url = os.environ.get("CREDIT_RADAR_DATABASE_URL")
    if not database_url:
        _fail("CREDIT_RADAR_DATABASE_URL is not set")

    name = _guard(database_url)
    _ensure_database(database_url)
    _migrate()

    # Imported after the guard, so a refusal cannot have touched anything.
    from credit_radar.persistence.models import CollectionRunRow, MarketObservationRow

    observations, runs = build_dataset(datetime.now(UTC))

    engine = create_engine(database_url)
    with Session(engine) as session:
        session.execute(text("TRUNCATE market_observations, collection_runs"))
        session.execute(MarketObservationRow.__table__.insert(), observations)
        session.execute(CollectionRunRow.__table__.insert(), runs)
        session.commit()
    engine.dispose()

    print(
        f"seed_e2e: {name} seeded with {len(observations)} synthetic observation(s) "
        f"and {len(runs)} run(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
