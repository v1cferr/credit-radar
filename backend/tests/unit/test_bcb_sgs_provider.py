"""Contract and normalization tests for the Banco Central SGS provider.

Every test runs against a mocked transport. Parsing is verified separately
from network interaction, so the suite stays deterministic and never depends
on the availability of an external service.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from credit_radar.domain.market import INDICATOR_CATALOG, IndicatorCode, Unit
from credit_radar.domain.provenance import CollectionStatus, SourceId
from credit_radar.providers.bcb.sgs import (
    COLLECTOR_VERSION,
    SGS_MAX_LATEST_VALUES,
    SGS_SERIES,
    BcbSgsProvider,
)
from credit_radar.providers.http import HttpClient
from tests.conftest import FROZEN_NOW

SGS_HOST = "https://api.bcb.gov.br"


@pytest.fixture
def provider(frozen_clock):
    with HttpClient(timeout_seconds=5.0, max_attempts=1) as http:
        yield BcbSgsProvider(http, clock=frozen_clock)


class TestSeriesMapping:
    def test_every_mapped_indicator_exists_in_the_catalog(self):
        assert set(SGS_SERIES).issubset(set(INDICATOR_CATALOG))

    def test_series_codes_are_distinct(self):
        # Two indicators sharing an upstream code would mean one of them is
        # mislabelled, which is how the market/regulated mortgage mix-up
        # would have reappeared.
        codes = list(SGS_SERIES.values())
        assert len(codes) == len(set(codes))

    def test_rejects_an_indicator_this_source_does_not_provide(self, provider, monkeypatch):
        # SGS currently backs every catalog indicator, so the guard is
        # exercised by removing one from the mapping rather than by relying
        # on the two sets staying different.
        withheld = IndicatorCode.SELIC_TARGET
        monkeypatch.setitem(SGS_SERIES, withheld, None)
        monkeypatch.delitem(SGS_SERIES, withheld)

        with pytest.raises(ValueError, match="not available"):
            provider.fetch_latest(withheld)

    def test_reports_which_indicators_it_supports(self, provider):
        assert set(provider.supported_indicators()) == set(SGS_SERIES)


class TestUpstreamLimits:
    def test_refuses_more_latest_values_than_the_api_accepts(self, provider):
        # The SGS API rejects a "latest N" request above 20 with HTTP 400
        # ("A quantidade maxima de valores deve ser 20"). Refusing locally
        # turns a confusing upstream 400 into a clear programming error.
        with pytest.raises(ValueError, match="at most 20 values"):
            provider.fetch_latest(IndicatorCode.SELIC_TARGET, count=90)

    def test_accepts_the_maximum_the_api_allows(self, provider, load_fixture):
        with respx.mock:
            respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
                return_value=httpx.Response(200, json=load_fixture("bcb/sgs_432_selic_target.json"))
            )
            outcome = provider.fetch_latest(IndicatorCode.SELIC_TARGET, count=SGS_MAX_LATEST_VALUES)

        assert outcome.run.status == CollectionStatus.SUCCESS

    def test_does_not_clamp_silently(self, provider):
        # Clamping would hand back 20 points to a caller that asked for 90
        # and let it treat them as the complete series.
        with pytest.raises(ValueError):
            provider.fetch_latest(IndicatorCode.SELIC_TARGET, count=SGS_MAX_LATEST_VALUES + 1)

    def test_range_requests_are_not_capped(self, provider, load_fixture):
        # The date-range form carries no upstream limit, which is what makes
        # backfilling history possible at all.
        with respx.mock:
            respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
                return_value=httpx.Response(200, json=load_fixture("bcb/sgs_432_selic_target.json"))
            )
            outcome = provider.fetch_range(
                IndicatorCode.SELIC_TARGET, start=date(2020, 1, 1), end=date(2026, 9, 16)
            )

        assert outcome.run.status == CollectionStatus.SUCCESS


class TestNormalization:
    @respx.mock
    def test_normalizes_a_captured_selic_target_payload(self, provider, load_fixture):
        payload = load_fixture("bcb/sgs_432_selic_target.json")
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(200, json=payload)
        )

        outcome = provider.fetch_range(
            IndicatorCode.SELIC_TARGET, start=date(2026, 9, 7), end=date(2026, 9, 16)
        )

        assert outcome.run.status == CollectionStatus.SUCCESS
        assert outcome.run.observation_count == 10
        assert len(outcome.observations) == 10

        first = outcome.observations[0]
        assert first.indicator_code == IndicatorCode.SELIC_TARGET
        assert first.reference_date == date(2026, 9, 7)
        assert first.value == Decimal("14.00")
        assert first.unit == Unit.PERCENT_PER_YEAR

    @respx.mock
    def test_keeps_observations_whose_reference_date_is_in_the_future(self, provider, load_fixture):
        # The captured payload was collected on 2026-09-09 and legitimately
        # contains dates through 2026-09-16, because the Copom publishes the
        # target ahead. Discarding them would drop valid data.
        payload = load_fixture("bcb/sgs_432_selic_target.json")
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(200, json=payload)
        )

        outcome = provider.fetch_range(
            IndicatorCode.SELIC_TARGET, start=date(2026, 9, 7), end=date(2026, 9, 16)
        )

        future = [o for o in outcome.observations if o.reference_date > FROZEN_NOW.date()]
        assert [o.reference_date for o in future] == [date(2026, 9, day) for day in range(10, 17)]

    @respx.mock
    def test_preserves_published_decimal_scale(self, provider, load_fixture):
        payload = load_fixture("bcb/sgs_20772_mortgage_market.json")
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.20772/dados").mock(
            return_value=httpx.Response(200, json=payload)
        )

        outcome = provider.fetch_range(
            IndicatorCode.MORTGAGE_RATE_MARKET_PF,
            start=date(2026, 5, 1),
            end=date(2026, 7, 1),
        )

        assert [str(o.value) for o in outcome.observations] == ["14.33", "14.31", "14.28"]

    @respx.mock
    def test_skips_rows_with_no_measurement(self, provider, load_fixture):
        # A blank value means the indicator was not measured. Storing it as
        # zero would invent a real rate of 0%.
        payload = load_fixture("bcb/sgs_synthetic_unmeasured_rows.json")
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.433/dados").mock(
            return_value=httpx.Response(200, json=payload)
        )

        outcome = provider.fetch_latest(IndicatorCode.IPCA_MONTHLY, count=4)

        assert outcome.run.status == CollectionStatus.SUCCESS
        assert [str(o.value) for o in outcome.observations] == ["1.10", "1.25"]
        assert outcome.run.observation_count == 2

    @respx.mock
    def test_monthly_series_are_dated_at_the_first_day_of_the_month(self, provider, load_fixture):
        payload = load_fixture("bcb/sgs_20772_mortgage_market.json")
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.20772/dados").mock(
            return_value=httpx.Response(200, json=payload)
        )

        outcome = provider.fetch_latest(IndicatorCode.MORTGAGE_RATE_MARKET_PF, count=3)

        assert all(o.reference_date.day == 1 for o in outcome.observations)


class TestProvenance:
    @respx.mock
    def test_records_full_provenance_for_every_observation(self, provider, load_fixture):
        payload = load_fixture("bcb/sgs_20772_mortgage_market.json")
        route = respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.20772/dados").mock(
            return_value=httpx.Response(200, json=payload)
        )

        outcome = provider.fetch_latest(IndicatorCode.MORTGAGE_RATE_MARKET_PF, count=3)

        provenance = outcome.observations[0].provenance
        assert provenance.source_id == SourceId.BCB_SGS
        assert provenance.source_reference == "bcdata.sgs.20772"
        assert provenance.collector_version == COLLECTOR_VERSION
        assert provenance.collected_at == FROZEN_NOW
        assert provenance.request_url == str(route.calls[0].request.url).split("?")[0]

    @respx.mock
    def test_requests_the_series_code_mapped_to_the_indicator(self, provider, load_fixture):
        # Guards the mapping itself: asking for the market mortgage rate must
        # not silently query the regulated series.
        route = respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.20772/dados").mock(
            return_value=httpx.Response(
                200, json=load_fixture("bcb/sgs_20772_mortgage_market.json")
            )
        )

        provider.fetch_latest(IndicatorCode.MORTGAGE_RATE_MARKET_PF, count=1)

        assert route.called
        assert "bcdata.sgs.20772" in str(route.calls[0].request.url)


class TestFailureHandling:
    @respx.mock
    def test_reports_no_data_when_the_source_returns_404(self, provider):
        # The SGS API answers a valid query with no matching rows using 404
        # and an error envelope, not an empty array.
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.433/dados").mock(
            return_value=httpx.Response(
                404, json={"erro": {"statusCode": 404, "detail": "Value(s) not found"}}
            )
        )

        outcome = provider.fetch_range(
            IndicatorCode.IPCA_MONTHLY, start=date(2030, 1, 1), end=date(2030, 2, 1)
        )

        assert outcome.run.status == CollectionStatus.NO_DATA
        assert outcome.observations == ()
        assert outcome.run.error_message is None

    @respx.mock
    def test_reports_failure_on_a_timeout(self, provider):
        # An invalid series code has been observed to hang until the client
        # timeout rather than return an error status.
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )

        outcome = provider.fetch_latest(IndicatorCode.SELIC_TARGET)

        assert outcome.run.status == CollectionStatus.FAILED
        assert outcome.observations == ()
        assert "timed out" in (outcome.run.error_message or "")

    @respx.mock
    def test_reports_failure_on_a_server_error(self, provider):
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(503)
        )

        outcome = provider.fetch_latest(IndicatorCode.SELIC_TARGET)

        assert outcome.run.status == CollectionStatus.FAILED
        assert "503" in (outcome.run.error_message or "")

    @respx.mock
    def test_reports_failure_when_the_payload_shape_changes(self, provider):
        # If SGS ever returns an object instead of an array, that is a
        # contract break to surface, not something to coerce.
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(200, json={"data": "09/09/2026", "valor": "14.00"})
        )

        outcome = provider.fetch_latest(IndicatorCode.SELIC_TARGET)

        assert outcome.run.status == CollectionStatus.FAILED
        assert "expected a JSON array" in (outcome.run.error_message or "")

    @respx.mock
    def test_reports_failure_when_a_row_is_missing_fields(self, provider):
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(200, json=[{"data": "09/09/2026"}])
        )

        outcome = provider.fetch_latest(IndicatorCode.SELIC_TARGET)

        assert outcome.run.status == CollectionStatus.FAILED
        assert "missing" in (outcome.run.error_message or "")

    @respx.mock
    def test_reports_failure_on_an_unparseable_date(self, provider):
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(200, json=[{"data": "2026-09-09", "valor": "14.00"}])
        )

        outcome = provider.fetch_latest(IndicatorCode.SELIC_TARGET)

        assert outcome.run.status == CollectionStatus.FAILED
        assert "dd/MM/yyyy" in (outcome.run.error_message or "")

    @respx.mock
    def test_records_an_audit_run_even_when_collection_fails(self, provider):
        # A run that produced nothing must still be attributable, otherwise a
        # gap in the history has no explanation.
        respx.get(url__startswith=f"{SGS_HOST}/dados/serie/bcdata.sgs.432/dados").mock(
            return_value=httpx.Response(503)
        )

        run = provider.fetch_latest(IndicatorCode.SELIC_TARGET).run

        assert run.source_id == SourceId.BCB_SGS
        assert run.source_reference == "bcdata.sgs.432"
        assert run.collector_version == COLLECTOR_VERSION
        assert run.started_at == FROZEN_NOW
        assert run.observation_count == 0
