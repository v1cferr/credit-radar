"""HTTP contract of the market endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from credit_radar.api.app import create_app
from credit_radar.api.dependencies import get_db_session, get_sgs_provider
from credit_radar.domain.market import IndicatorCode, MarketObservation, Unit
from credit_radar.domain.provenance import Provenance, SourceId
from credit_radar.persistence.repositories import MarketObservationRepository
from credit_radar.providers.bcb.sgs import BcbSgsProvider
from credit_radar.providers.http import HttpClient
from tests.conftest import FROZEN_NOW

pytestmark = pytest.mark.integration

SGS_HOST = "https://api.bcb.gov.br"


@pytest.fixture
def client(session, frozen_clock):
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    def override_provider() -> Iterator[BcbSgsProvider]:
        with HttpClient(timeout_seconds=5.0, max_attempts=1) as http:
            yield BcbSgsProvider(http, clock=frozen_clock)

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_sgs_provider] = override_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def selic(value: str, reference_date: date) -> MarketObservation:
    return MarketObservation(
        indicator_code=IndicatorCode.SELIC_TARGET,
        reference_date=reference_date,
        value=value,  # type: ignore[arg-type]
        unit=Unit.PERCENT_PER_YEAR,
        provenance=Provenance(
            source_id=SourceId.BCB_SGS,
            source_reference="bcdata.sgs.432",
            collector="credit_radar.providers.bcb.sgs",
            collector_version="1",
            collected_at=FROZEN_NOW,
        ),
    )


class TestHealth:
    def test_reports_database_reachability(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "reachable"}


class TestIndicatorCatalog:
    def test_lists_every_tracked_indicator(self, client):
        response = client.get("/api/v1/market/indicators")

        assert response.status_code == 200
        codes = {item["code"] for item in response.json()}
        assert "SELIC_TARGET" in codes
        # Both mortgage regimes are exposed separately; collapsing them would
        # let the UI benchmark an offer against the wrong average.
        assert {"MORTGAGE_RATE_MARKET_PF", "MORTGAGE_RATE_REGULATED_PF"} <= codes

    def test_reports_the_unit_of_each_indicator(self, client):
        response = client.get("/api/v1/market/indicators")

        by_code = {item["code"]: item for item in response.json()}
        assert by_code["SELIC_TARGET"]["unit"] == "percent_per_year"


class TestSummary:
    def test_reports_null_latest_when_nothing_was_collected(self, client):
        # The dashboard must be able to say "no observations yet" instead of
        # rendering a zero that would read as a real rate.
        response = client.get("/api/v1/market/summary")

        assert response.status_code == 200
        summaries = {i["indicator"]["code"]: i for i in response.json()["indicators"]}
        assert summaries["SELIC_TARGET"]["latest"] is None
        assert summaries["SELIC_TARGET"]["last_run"] is None

    def test_reports_the_current_value_once_collected(self, client, session):
        MarketObservationRepository(session).add_all([selic("14.00", date(2026, 9, 9))])
        session.flush()

        response = client.get("/api/v1/market/summary")

        summaries = {i["indicator"]["code"]: i for i in response.json()["indicators"]}
        assert summaries["SELIC_TARGET"]["latest"]["value"] == "14.00"


class TestObservationSerialization:
    def test_values_are_serialized_as_strings(self, client, session):
        # A JSON number becomes an IEEE-754 double in the browser, so "14.00"
        # would arrive as 14 and the published scale would be lost.
        MarketObservationRepository(session).add_all([selic("14.00", date(2026, 9, 9))])
        session.flush()

        response = client.get("/api/v1/market/indicators/SELIC_TARGET/observations/latest")

        assert response.status_code == 200
        assert response.json()["value"] == "14.00"
        assert isinstance(response.json()["value"], str)

    def test_exposes_provenance_for_the_ui(self, client, session):
        MarketObservationRepository(session).add_all([selic("14.00", date(2026, 9, 9))])
        session.flush()

        response = client.get("/api/v1/market/indicators/SELIC_TARGET/observations/latest")

        provenance = response.json()["provenance"]
        assert provenance["source_id"] == "bcb.sgs"
        assert provenance["source_reference"] == "bcdata.sgs.432"
        assert provenance["collected_at"].startswith("2026-09-09")

    def test_returns_404_when_an_indicator_has_no_observations(self, client):
        response = client.get("/api/v1/market/indicators/IGPM_MONTHLY/observations/latest")

        assert response.status_code == 404

    def test_rejects_an_unknown_indicator_code(self, client):
        response = client.get("/api/v1/market/indicators/NOT_AN_INDICATOR/observations/latest")

        assert response.status_code == 422


class TestHistory:
    def test_returns_the_series_oldest_first(self, client, session):
        MarketObservationRepository(session).add_all(
            [
                selic("15.00", date(2026, 9, 7)),
                selic("14.00", date(2026, 9, 9)),
                selic("14.50", date(2026, 9, 8)),
            ]
        )
        session.flush()

        response = client.get("/api/v1/market/indicators/SELIC_TARGET/observations")

        observations = response.json()["observations"]
        assert [o["reference_date"] for o in observations] == [
            "2026-09-07",
            "2026-09-08",
            "2026-09-09",
        ]

    def test_can_be_bounded_by_date(self, client, session):
        MarketObservationRepository(session).add_all(
            [selic("15.00", date(2026, 9, 7)), selic("14.00", date(2026, 9, 9))]
        )
        session.flush()

        response = client.get(
            "/api/v1/market/indicators/SELIC_TARGET/observations",
            params={"from": "2026-09-08", "to": "2026-09-30"},
        )

        assert [o["value"] for o in response.json()["observations"]] == ["14.00"]

    def test_rejects_an_inverted_date_range(self, client):
        response = client.get(
            "/api/v1/market/indicators/SELIC_TARGET/observations",
            params={"from": "2026-09-30", "to": "2026-09-01"},
        )

        assert response.status_code == 422

    def test_returns_an_empty_series_rather_than_404(self, client):
        # An empty history is a valid answer for a known indicator; the UI
        # renders an empty state, not an error.
        response = client.get("/api/v1/market/indicators/IGPM_MONTHLY/observations")

        assert response.status_code == 200
        assert response.json()["observations"] == []
        assert response.json()["indicator"]["code"] == "IGPM_MONTHLY"


class TestIngestion:
    @respx.mock
    def test_ingests_and_then_serves_the_collected_data(self, client, load_fixture):
        payload = load_fixture("bcb/sgs_432_selic_target.json")
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(200, json=payload)
        )

        ingest = client.post("/api/v1/market/indicators/SELIC_TARGET/ingest")

        assert ingest.status_code == 200
        body = ingest.json()
        assert body["collected"] == 10
        assert body["stored"] == 10
        assert body["run"]["status"] == "success"

        history = client.get("/api/v1/market/indicators/SELIC_TARGET/observations")
        assert len(history.json()["observations"]) == 10

    @respx.mock
    def test_re_ingesting_stores_nothing_new(self, client, load_fixture):
        payload = load_fixture("bcb/sgs_432_selic_target.json")
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(200, json=payload)
        )

        client.post("/api/v1/market/indicators/SELIC_TARGET/ingest")
        second = client.post("/api/v1/market/indicators/SELIC_TARGET/ingest")

        assert second.json()["collected"] == 10
        assert second.json()["stored"] == 0

    @respx.mock
    def test_reports_a_failed_run_without_raising(self, client):
        # A provider outage is an expected condition, surfaced as data so the
        # UI can show a stale-source warning rather than a broken page.
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(503)
        )

        response = client.post("/api/v1/market/indicators/SELIC_TARGET/ingest")

        assert response.status_code == 200
        assert response.json()["run"]["status"] == "failed"
        assert response.json()["stored"] == 0

    @respx.mock
    def test_records_the_run_in_the_summary(self, client, load_fixture):
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(200, json=load_fixture("bcb/sgs_432_selic_target.json"))
        )

        client.post("/api/v1/market/indicators/SELIC_TARGET/ingest")
        summary = client.get("/api/v1/market/summary")

        summaries = {i["indicator"]["code"]: i for i in summary.json()["indicators"]}
        assert summaries["SELIC_TARGET"]["last_run"]["status"] == "success"
        assert summaries["SELIC_TARGET"]["last_run"]["observation_count"] == 10


class TestSafetyInvariant:
    def test_the_api_exposes_no_write_beyond_collection(self, client):
        # CreditRadar must never be able to create a financial obligation.
        # Guard the surface: the only non-GET route may be data collection.
        spec = client.get("/openapi.json").json()
        mutating = {
            (path, method)
            for path, operations in spec["paths"].items()
            for method in operations
            if method.upper() not in {"GET", "HEAD", "OPTIONS"}
        }

        assert mutating == {("/api/v1/market/indicators/{code}/ingest", "post")}
