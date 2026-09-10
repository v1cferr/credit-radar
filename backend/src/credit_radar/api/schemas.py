"""Request and response models for the HTTP API.

Financial values are serialized as JSON *strings*, not numbers. A JSON
number is an IEEE-754 double once it reaches the browser, so a rate stored
as "14.00" would arrive as 14 and a settlement amount could arrive slightly
wrong. Sending the decimal as text preserves both the exact value and the
scale the source published; the frontend formats it for display.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from credit_radar.domain.market import (
    Frequency,
    IndicatorCode,
    IndicatorKind,
    MarketIndicator,
    MarketObservation,
    Unit,
)
from credit_radar.domain.provenance import CollectionRun, CollectionStatus


class ProvenanceResponse(BaseModel):
    """Where a value came from, exposed so the UI can show it to the user."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    source_reference: str
    collector_version: str
    collected_at: datetime

    @classmethod
    def from_domain(cls, observation: MarketObservation) -> ProvenanceResponse:
        provenance = observation.provenance
        return cls(
            source_id=provenance.source_id.value,
            source_reference=provenance.source_reference,
            collector_version=provenance.collector_version,
            collected_at=provenance.collected_at,
        )


class IndicatorResponse(BaseModel):
    """What an indicator measures."""

    model_config = ConfigDict(frozen=True)

    code: IndicatorCode
    name: str
    kind: IndicatorKind
    unit: Unit
    frequency: Frequency
    description: str

    @classmethod
    def from_domain(cls, indicator: MarketIndicator) -> IndicatorResponse:
        return cls(
            code=indicator.code,
            name=indicator.name,
            kind=indicator.kind,
            unit=indicator.unit,
            frequency=indicator.frequency,
            description=indicator.description,
        )


class ObservationResponse(BaseModel):
    """One value of one indicator, with its provenance."""

    model_config = ConfigDict(frozen=True)

    indicator_code: IndicatorCode
    reference_date: date
    value: Decimal
    unit: Unit
    provenance: ProvenanceResponse

    @field_serializer("value")
    def _serialize_value(self, value: Decimal) -> str:
        return str(value)

    @classmethod
    def from_domain(cls, observation: MarketObservation) -> ObservationResponse:
        return cls(
            indicator_code=observation.indicator_code,
            reference_date=observation.reference_date,
            value=observation.value,
            unit=observation.unit,
            provenance=ProvenanceResponse.from_domain(observation),
        )


class CollectionRunResponse(BaseModel):
    """The outcome of the most recent collection attempt against a source."""

    model_config = ConfigDict(frozen=True)

    status: CollectionStatus
    started_at: datetime
    finished_at: datetime
    observation_count: int
    error_message: str | None

    @classmethod
    def from_domain(cls, run: CollectionRun) -> CollectionRunResponse:
        return cls(
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            observation_count=run.observation_count,
            error_message=run.error_message,
        )


class IndicatorSummary(BaseModel):
    """An indicator, its current value and the health of its last collection.

    ``latest`` is null when nothing has been collected yet. That is a real
    state the UI must render as "no observations yet" rather than as a zero,
    which is why it is modelled explicitly instead of defaulted.
    """

    model_config = ConfigDict(frozen=True)

    indicator: IndicatorResponse
    latest: ObservationResponse | None
    last_run: CollectionRunResponse | None


class MarketSummaryResponse(BaseModel):
    """Everything the market dashboard needs in one request."""

    model_config = ConfigDict(frozen=True)

    indicators: list[IndicatorSummary]


class ObservationSeriesResponse(BaseModel):
    """A history series for charting."""

    model_config = ConfigDict(frozen=True)

    indicator: IndicatorResponse
    observations: list[ObservationResponse]


class IngestionResponse(BaseModel):
    """Result of an explicitly requested collection."""

    model_config = ConfigDict(frozen=True)

    indicator_code: IndicatorCode
    collected: int
    stored: int
    run: CollectionRunResponse


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    database: str
