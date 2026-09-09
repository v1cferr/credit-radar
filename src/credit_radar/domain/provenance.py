"""Provenance: where an observed value came from, and how it got here.

Every externally collected value in CreditRadar carries its provenance. The
project's long-term asset is a historical dataset, and a historical dataset
whose values cannot be traced back to a source and a collection time is not
auditable -- it is just numbers.

Provenance must be able to answer:

- Where did this value come from?      -> source_id, source_reference
- When was it collected?               -> collected_at
- Which provider produced it?          -> source_id
- What version/parser collected it?    -> collector, collector_version
- Was collection successful?           -> CollectionRun.status
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceId(StrEnum):
    """Stable identifier of an external data source.

    Sources are namespaced by institution so that a single institution can
    expose several independent integrations (for example, the Banco Central
    SGS time-series API and, later, Registrato/SCR reports) without the two
    being confused for one another in the historical record.
    """

    BCB_SGS = "bcb.sgs"


class CollectionStatus(StrEnum):
    """Outcome of a single collection attempt."""

    SUCCESS = "success"
    """The source answered and the response was parsed."""

    NO_DATA = "no_data"
    """The source answered authoritatively that it has no data for the request.

    This is a successful interaction with an empty result, not a failure. The
    distinction matters: it separates "the collector ran and the source had
    nothing" from "the collector never ran".
    """

    FAILED = "failed"
    """The source could not be reached, or its response could not be parsed."""


def _require_utc(value: datetime) -> datetime:
    """Reject naive datetimes and normalize to UTC.

    Timestamps in the historical record are compared across collection runs
    that may happen in different processes and, eventually, on different
    machines. A naive datetime silently makes those comparisons wrong, so it
    is rejected at the domain boundary rather than normalized by guessing.
    """
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware; naive datetimes are ambiguous")
    return value.astimezone(UTC)


class Provenance(BaseModel):
    """The origin of a single observed value."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: SourceId
    source_reference: str = Field(min_length=1)
    """The source's own identifier for the series, as the source names it.

    Kept verbatim (for example ``bcdata.sgs.432``) so a stored observation can
    be traced back to the exact upstream series without reverse-engineering
    our internal naming.
    """

    collector: str = Field(min_length=1)
    """Dotted path of the code that produced this value."""

    collector_version: str = Field(min_length=1)
    """Version of the parsing logic, bumped whenever normalization changes.

    Without this, a normalization bug fixed today is indistinguishable from
    correct data collected yesterday.
    """

    collected_at: datetime
    """When CreditRadar observed the value -- not the date the value refers to."""

    request_url: str | None = None
    """The exact request that produced the value, when the source is an HTTP API."""

    _normalize_collected_at = field_validator("collected_at")(_require_utc)


class CollectionRun(BaseModel):
    """Audit record of one collection attempt against one source.

    Recorded whether or not the attempt produced observations, so gaps in the
    historical series can be explained after the fact. Runs cannot be
    backfilled: an attempt that was never recorded is lost, which is why this
    exists before there is anything to debug.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: SourceId
    source_reference: str = Field(min_length=1)
    collector: str = Field(min_length=1)
    collector_version: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime
    status: CollectionStatus
    observation_count: int = Field(ge=0)
    error_message: str | None = None
    """Failure summary. Must never contain credentials or personal data."""

    _normalize_started_at = field_validator("started_at")(_require_utc)
    _normalize_finished_at = field_validator("finished_at")(_require_utc)
