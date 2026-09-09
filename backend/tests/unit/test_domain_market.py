"""Domain invariants for market indicators and provenance."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from credit_radar.domain.market import (
    INDICATOR_CATALOG,
    IndicatorCode,
    MarketObservation,
    Unit,
)
from credit_radar.domain.provenance import Provenance, SourceId


def make_provenance(**overrides: object) -> Provenance:
    defaults: dict[str, object] = {
        "source_id": SourceId.BCB_SGS,
        "source_reference": "bcdata.sgs.432",
        "collector": "credit_radar.providers.bcb.sgs",
        "collector_version": "1",
        "collected_at": datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
    }
    return Provenance(**(defaults | overrides))  # type: ignore[arg-type]


class TestProvenance:
    def test_rejects_naive_collected_at(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            make_provenance(collected_at=datetime(2026, 9, 9, 12, 0))

    def test_normalizes_offset_aware_timestamp_to_utc(self):
        sao_paulo = timezone(timedelta(hours=-3))
        provenance = make_provenance(collected_at=datetime(2026, 9, 9, 9, 0, tzinfo=sao_paulo))

        assert provenance.collected_at == datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
        assert provenance.collected_at.tzinfo == UTC

    def test_is_immutable(self):
        provenance = make_provenance()
        with pytest.raises(ValidationError):
            provenance.source_reference = "tampered"  # type: ignore[misc]

    def test_keeps_upstream_series_reference_verbatim(self):
        # Traceability depends on storing the source's own identifier, not a
        # translation of it.
        assert make_provenance().source_reference == "bcdata.sgs.432"


class TestMarketObservation:
    def test_accepts_decimal_and_string_values(self):
        from_string = MarketObservation(
            indicator_code=IndicatorCode.SELIC_TARGET,
            reference_date=date(2026, 9, 9),
            value="14.00",  # type: ignore[arg-type]
            unit=Unit.PERCENT_PER_YEAR,
            provenance=make_provenance(),
        )
        assert from_string.value == Decimal("14.00")

    def test_rejects_float_value(self):
        # Decimal(0.1) != 0.1. Silent precision loss is unacceptable in data
        # used to compare settlement offers and financing costs.
        with pytest.raises(ValidationError, match="must not be built from float"):
            MarketObservation(
                indicator_code=IndicatorCode.SELIC_TARGET,
                reference_date=date(2026, 9, 9),
                value=14.00,  # type: ignore[arg-type]
                unit=Unit.PERCENT_PER_YEAR,
                provenance=make_provenance(),
            )

    def test_preserves_scale_of_source_value(self):
        # "13.90" and "13.9" are the same number but not the same published
        # precision; the source's scale is part of the record.
        observation = MarketObservation(
            indicator_code=IndicatorCode.SELIC_ANNUALIZED,
            reference_date=date(2026, 9, 9),
            value="13.90",  # type: ignore[arg-type]
            unit=Unit.PERCENT_PER_YEAR,
            provenance=make_provenance(),
        )
        assert str(observation.value) == "13.90"

    def test_rejects_unit_that_contradicts_the_catalog(self):
        # A per-day value labelled per-year is a plausible-looking number
        # that would skew every downstream comparison.
        with pytest.raises(ValidationError, match="declares percent_per_day"):
            MarketObservation(
                indicator_code=IndicatorCode.SELIC_ANNUALIZED,
                reference_date=date(2026, 9, 9),
                value="0.051660",  # type: ignore[arg-type]
                unit=Unit.PERCENT_PER_DAY,
                provenance=make_provenance(),
            )

    def test_allows_reference_date_in_the_future(self):
        # The Copom publishes the Selic target for dates that have not
        # happened yet. Verified against the live SGS API: on 2026-09-09,
        # series 432 returned an observation dated 2026-09-16.
        collected_at = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
        observation = MarketObservation(
            indicator_code=IndicatorCode.SELIC_TARGET,
            reference_date=date(2026, 9, 16),
            value="14.00",  # type: ignore[arg-type]
            unit=Unit.PERCENT_PER_YEAR,
            provenance=make_provenance(collected_at=collected_at),
        )

        assert observation.reference_date > collected_at.date()

    def test_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            MarketObservation(
                indicator_code=IndicatorCode.SELIC_TARGET,
                reference_date=date(2026, 9, 9),
                value=Decimal("14.00"),
                unit=Unit.PERCENT_PER_YEAR,
                provenance=make_provenance(),
                confidence="high",  # type: ignore[call-arg]
            )


class TestIndicatorCatalog:
    def test_every_indicator_code_is_defined(self):
        # A code without a definition would let an observation be stored with
        # no stated meaning or unit.
        assert set(INDICATOR_CATALOG) == set(IndicatorCode)

    def test_catalog_is_keyed_consistently(self):
        for code, indicator in INDICATOR_CATALOG.items():
            assert indicator.code == code

    def test_selic_target_is_a_daily_annual_policy_rate(self):
        selic = INDICATOR_CATALOG[IndicatorCode.SELIC_TARGET]
        assert selic.unit == Unit.PERCENT_PER_YEAR
        assert selic.frequency.value == "daily"
