"""The collection command against a real database and a mocked provider."""

from __future__ import annotations

import logging
from datetime import date

import httpx
import pytest
import respx

from credit_radar.cli import collect
from credit_radar.domain.market import IndicatorCode
from credit_radar.persistence.repositories import (
    CollectionRunRepository,
    MarketObservationRepository,
)

pytestmark = pytest.mark.integration

SGS_HOST = "https://api.bcb.gov.br"


@pytest.fixture
def wired_session(engine, monkeypatch):
    """Point the command's own session factory at the test database.

    The command opens a session per indicator on purpose, so it cannot be
    handed a session the way the API tests are; it has to be given a factory.

    This cleans up after itself rather than leaning on the `session` fixture,
    which it does not use. Without that, rows committed by one test survive
    into the next and the suite silently becomes order-dependent: a test
    asserting that a collection stores something passes or fails depending on
    whether an earlier test already stored it.
    """
    from sqlalchemy.orm import sessionmaker

    import credit_radar.persistence.database as database
    from credit_radar.persistence.models import Base

    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(database, "get_session_factory", lambda: factory)

    yield factory

    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


def mock_series(series: str, payload: object) -> None:
    respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.{series}/dados").mock(
        return_value=httpx.Response(200, json=payload)
    )


class TestCollect:
    @respx.mock
    def test_stores_what_it_collects(self, wired_session, load_fixture):
        mock_series("432", load_fixture("bcb/sgs_432_selic_target.json"))

        exit_code = collect([IndicatorCode.SELIC_TARGET], pause_seconds=0, today=date(2026, 9, 10))

        assert exit_code == 0
        with wired_session() as session:
            history = MarketObservationRepository(session).history(IndicatorCode.SELIC_TARGET)
        assert len(history) == 10

    @respx.mock
    def test_a_second_run_stores_nothing_new(self, wired_session, load_fixture):
        mock_series("432", load_fixture("bcb/sgs_432_selic_target.json"))

        collect([IndicatorCode.SELIC_TARGET], pause_seconds=0, today=date(2026, 9, 10))
        collect([IndicatorCode.SELIC_TARGET], pause_seconds=0, today=date(2026, 9, 10))

        with wired_session() as session:
            revisions = MarketObservationRepository(session).revisions(
                IndicatorCode.SELIC_TARGET, date(2026, 9, 7)
            )
        assert len(revisions) == 1

    @respx.mock
    def test_records_an_audit_run_even_when_the_provider_fails(self, wired_session):
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(503)
        )

        collect([IndicatorCode.SELIC_TARGET], pause_seconds=0, today=date(2026, 9, 10))

        with wired_session() as session:
            run = CollectionRunRepository(session).last_run("bcdata.sgs.432")
        assert run is not None
        assert run.status.value == "failed"


class TestExitCode:
    @respx.mock
    def test_one_failure_among_several_is_not_an_incident(self, wired_session, load_fixture):
        # A single flaky upstream series is recorded as data and shown in the
        # dashboard. A unit that goes red for it trains you to ignore red units.
        mock_series("432", load_fixture("bcb/sgs_432_selic_target.json"))
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.433/dados").mock(
            return_value=httpx.Response(503)
        )

        exit_code = collect(
            [IndicatorCode.SELIC_TARGET, IndicatorCode.IPCA_MONTHLY],
            pause_seconds=0,
            today=date(2026, 9, 10),
        )

        assert exit_code == 0

    @respx.mock
    def test_every_indicator_failing_is_an_incident(self, wired_session):
        # Points at the network or the configuration rather than at one
        # upstream series, so it should be visible as a failed unit.
        for series in ("432", "433"):
            respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.{series}/dados").mock(
                return_value=httpx.Response(503)
            )

        exit_code = collect(
            [IndicatorCode.SELIC_TARGET, IndicatorCode.IPCA_MONTHLY],
            pause_seconds=0,
            today=date(2026, 9, 10),
        )

        assert exit_code == 1

    @respx.mock
    def test_no_data_upstream_is_not_a_failure(self, wired_session):
        # The SGS API answers a valid query with no rows using 404.
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(404, json={"erro": {"detail": "Value(s) not found"}})
        )

        exit_code = collect([IndicatorCode.SELIC_TARGET], pause_seconds=0, today=date(2026, 9, 10))

        assert exit_code == 0


class TestQuietMode:
    @respx.mock
    def test_quiet_says_nothing_when_nothing_changed(self, wired_session, load_fixture, caplog):
        # Seven "same as yesterday" lines a day is a journal nobody reads.
        mock_series("432", load_fixture("bcb/sgs_432_selic_target.json"))
        collect([IndicatorCode.SELIC_TARGET], pause_seconds=0, today=date(2026, 9, 10))

        with caplog.at_level(logging.INFO, logger="credit_radar.collect"):
            collect(
                [IndicatorCode.SELIC_TARGET],
                pause_seconds=0,
                quiet=True,
                today=date(2026, 9, 10),
            )

        assert caplog.records == []

    @respx.mock
    def test_quiet_still_reports_a_change(self, wired_session, load_fixture, caplog):
        mock_series("432", load_fixture("bcb/sgs_432_selic_target.json"))

        with caplog.at_level(logging.INFO, logger="credit_radar.collect"):
            collect(
                [IndicatorCode.SELIC_TARGET],
                pause_seconds=0,
                quiet=True,
                today=date(2026, 9, 10),
            )

        assert any("stored=10" in r.getMessage() for r in caplog.records)

    @respx.mock
    def test_quiet_still_reports_a_failure(self, wired_session, caplog):
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(503)
        )

        with caplog.at_level(logging.WARNING, logger="credit_radar.collect"):
            collect(
                [IndicatorCode.SELIC_TARGET],
                pause_seconds=0,
                quiet=True,
                today=date(2026, 9, 10),
            )

        assert any(r.levelno >= logging.WARNING for r in caplog.records)
