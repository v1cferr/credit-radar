"""Market indicators and their observations.

The model follows the shape that the whole system is built on:

    Entity + Observation + Source + ObservedAt

A ``MarketIndicator`` is the *thing being measured* and is stable over time.
A ``MarketObservation`` is *one measured value* of it, carrying the date the
value refers to and the provenance of how it was obtained. State is never
overwritten: history is the product.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from credit_radar.domain.provenance import Provenance


class Unit(StrEnum):
    """Unit of an observed value.

    Rates are kept in the unit the source publishes them in. Converting a
    daily rate to an annual one is an analysis step with its own assumptions
    (252 vs 365 days), so it must not be hidden inside ingestion.
    """

    PERCENT_PER_YEAR = "percent_per_year"
    PERCENT_PER_MONTH = "percent_per_month"
    PERCENT_PER_DAY = "percent_per_day"
    INDEX_POINTS = "index_points"


class Frequency(StrEnum):
    """How often a series publishes a new value."""

    DAILY = "daily"
    """One value per calendar day, including weekends and holidays."""

    BUSINESS_DAILY = "business_daily"
    """One value per business day only."""

    MONTHLY = "monthly"


class IndicatorKind(StrEnum):
    """What kind of economic quantity an indicator measures.

    Distinguishes a policy rate set by the central bank from an observed
    market average, because they answer different questions: the first is a
    macroeconomic condition, the second is a benchmark to judge whether a
    specific offer is competitive.
    """

    POLICY_RATE = "policy_rate"
    MARKET_INTEREST_RATE = "market_interest_rate"
    INFLATION_INDEX = "inflation_index"


class IndicatorCode(StrEnum):
    """Internal, stable identity of a tracked indicator.

    Deliberately independent of any source's numbering: if a series is ever
    republished under a new upstream code, or the same concept becomes
    available from a second source, the internal code and its accumulated
    history stay intact.
    """

    SELIC_TARGET = "SELIC_TARGET"
    SELIC_ANNUALIZED = "SELIC_ANNUALIZED"
    IPCA_MONTHLY = "IPCA_MONTHLY"
    IGPM_MONTHLY = "IGPM_MONTHLY"
    VEHICLE_FINANCING_RATE_PF = "VEHICLE_FINANCING_RATE_PF"
    MORTGAGE_FINANCING_RATE_PF = "MORTGAGE_FINANCING_RATE_PF"


class MarketIndicator(BaseModel):
    """A quantity CreditRadar tracks over time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: IndicatorCode
    name: str = Field(min_length=1)
    kind: IndicatorKind
    unit: Unit
    frequency: Frequency
    description: str = Field(min_length=1)


class MarketObservation(BaseModel):
    """One value of one indicator, at one reference date, from one source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    indicator_code: IndicatorCode

    reference_date: date
    """The date the value refers to, as stated by the source.

    Distinct from ``provenance.collected_at``, and not bounded by it: the
    Copom's Selic target is published for dates that have not happened yet,
    so a reference date in the future is valid data, not a clock error.
    """

    value: Decimal
    unit: Unit
    provenance: Provenance

    @field_validator("value", mode="before")
    @classmethod
    def _reject_float(cls, value: Any) -> Any:
        """Refuse float input for a financial value.

        ``Decimal(0.1)`` is not 0.1. Pydantic would happily coerce a float
        here, which is exactly the silent precision loss that has no place in
        a dataset used to compare settlement offers and financing costs.
        Callers must pass a string, an int or a Decimal.
        """
        if isinstance(value, float):
            raise ValueError(
                "financial values must not be built from float; pass str, int or Decimal"
            )
        return value


INDICATOR_CATALOG: dict[IndicatorCode, MarketIndicator] = {
    indicator.code: indicator
    for indicator in (
        MarketIndicator(
            code=IndicatorCode.SELIC_TARGET,
            name="Selic target rate",
            kind=IndicatorKind.POLICY_RATE,
            unit=Unit.PERCENT_PER_YEAR,
            frequency=Frequency.DAILY,
            description=(
                "Selic target set by the Copom. Published ahead of time and held "
                "constant until the next Copom decision, so its reference dates "
                "extend into the future."
            ),
        ),
        MarketIndicator(
            code=IndicatorCode.SELIC_ANNUALIZED,
            name="Selic rate, annualized (252 business days)",
            kind=IndicatorKind.POLICY_RATE,
            unit=Unit.PERCENT_PER_YEAR,
            frequency=Frequency.BUSINESS_DAILY,
            description=(
                "Effective Selic rate actually practised in the market, annualized "
                "on a 252-business-day basis. Tracks the target closely but is not "
                "identical to it."
            ),
        ),
        MarketIndicator(
            code=IndicatorCode.IPCA_MONTHLY,
            name="IPCA, monthly change",
            kind=IndicatorKind.INFLATION_INDEX,
            unit=Unit.PERCENT_PER_MONTH,
            frequency=Frequency.MONTHLY,
            description=(
                "Brazil's headline consumer inflation index. Subject to upstream "
                "revision, which is why observations are stored as revisions "
                "rather than overwritten."
            ),
        ),
        MarketIndicator(
            code=IndicatorCode.IGPM_MONTHLY,
            name="IGP-M, monthly change",
            kind=IndicatorKind.INFLATION_INDEX,
            unit=Unit.PERCENT_PER_MONTH,
            frequency=Frequency.MONTHLY,
            description=(
                "General price index used as an indexer in several contract types, "
                "including real-estate agreements."
            ),
        ),
        MarketIndicator(
            code=IndicatorCode.VEHICLE_FINANCING_RATE_PF,
            name="Average vehicle financing rate, individuals",
            kind=IndicatorKind.MARKET_INTEREST_RATE,
            unit=Unit.PERCENT_PER_YEAR,
            frequency=Frequency.MONTHLY,
            description=(
                "Average interest rate charged to individuals on vehicle "
                "acquisition credit. The benchmark for judging whether a specific "
                "vehicle financing offer is competitive."
            ),
        ),
        MarketIndicator(
            code=IndicatorCode.MORTGAGE_FINANCING_RATE_PF,
            name="Average mortgage financing rate, individuals",
            kind=IndicatorKind.MARKET_INTEREST_RATE,
            unit=Unit.PERCENT_PER_YEAR,
            frequency=Frequency.MONTHLY,
            description=(
                "Average interest rate charged to individuals on market-rate real "
                "estate financing. Excludes subsidized housing programmes, whose "
                "rates are not comparable."
            ),
        ),
    )
}
"""Domain definition of each tracked indicator.

Holds only what the indicator *means*. The mapping from an indicator to a
particular source's series identifier is provider knowledge and lives with
the provider.
"""
