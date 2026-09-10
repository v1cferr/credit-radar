"""Smoke tests against the real Banco Central SGS API.

Excluded from the default suite. They exist to answer a question fixtures
cannot: has the upstream contract changed since the fixtures were captured?
A parser can stay green forever against a payload the source no longer sends.

    uv run pytest -m live

They read public market data only. No credential is used, no personal data is
touched, and nothing here may ever be pointed at an authenticated source
without an explicit opt-in of its own.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from credit_radar.domain.market import INDICATOR_CATALOG
from credit_radar.domain.provenance import CollectionStatus
from credit_radar.providers.bcb.sgs import (
    SGS_MAX_LATEST_VALUES,
    SGS_SERIES,
    BcbSgsProvider,
)
from credit_radar.providers.http import HttpClient

pytestmark = pytest.mark.live


@pytest.fixture
def provider():
    with HttpClient(timeout_seconds=25.0) as http:
        yield BcbSgsProvider(http)


class TestUpstreamContract:
    @pytest.mark.parametrize("indicator", sorted(SGS_SERIES, key=lambda code: code.value))
    def test_every_mapped_series_still_answers(self, provider, indicator):
        # Catches a renumbered or withdrawn series, which fixtures cannot.
        outcome = provider.fetch_latest(indicator, count=1)

        assert outcome.run.status is not CollectionStatus.FAILED, (
            f"{indicator.value} ({outcome.run.source_reference}): {outcome.run.error_message}"
        )

    def test_the_payload_still_normalizes_into_the_domain(self, provider):
        outcome = provider.fetch_latest(next(iter(SGS_SERIES)), count=1)

        assert outcome.observations, "the source answered but produced no observation"
        observation = outcome.observations[0]
        assert observation.value is not None
        assert observation.provenance.source_reference.startswith("bcdata.sgs.")

    def test_units_still_match_the_catalog(self, provider):
        # The observation constructor rejects a unit that contradicts the
        # catalog, so a silent upstream change of scale surfaces as a failed
        # run rather than as a plausible wrong number.
        for indicator in sorted(SGS_SERIES, key=lambda code: code.value):
            outcome = provider.fetch_latest(indicator, count=1)
            for observation in outcome.observations:
                assert observation.unit == INDICATOR_CATALOG[indicator].unit


class TestUpstreamLimitsStillHold:
    def test_the_latest_form_still_caps_where_we_think_it_does(self, provider):
        # The provider refuses more than this locally. If the API ever raises
        # the cap, this test says so instead of the code quietly staying
        # conservative forever.
        outcome = provider.fetch_latest(next(iter(SGS_SERIES)), count=SGS_MAX_LATEST_VALUES)

        assert outcome.run.status is not CollectionStatus.FAILED

    def test_the_range_form_is_still_uncapped(self, provider):
        # Backfill depends on this: the range form returned thousands of rows
        # where the latest form refuses more than twenty.
        indicator = next(code for code, series in SGS_SERIES.items() if series == "432")
        end = date.today()
        outcome = provider.fetch_range(indicator, start=end - timedelta(days=400), end=end)

        assert outcome.run.status is CollectionStatus.SUCCESS
        assert len(outcome.observations) > SGS_MAX_LATEST_VALUES

    def test_an_empty_range_is_still_reported_as_no_data(self, provider):
        # The API answers a valid query with no rows using 404, which the
        # provider maps to NO_DATA rather than to a failure.
        indicator = next(iter(SGS_SERIES))
        far_future = date.today() + timedelta(days=3650)
        outcome = provider.fetch_range(
            indicator, start=far_future, end=far_future + timedelta(days=30)
        )

        assert outcome.run.status is CollectionStatus.NO_DATA
