"""SQLAlchemy mappings for the historical record.

Two tables, both append-only:

``market_observations`` holds every value ever collected. Nothing is updated
in place, because the history is the product rather than a cache of the
present.

``collection_runs`` holds one row per collection attempt, successful or not,
so a gap in the series can be explained afterwards.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from credit_radar.domain.market import IndicatorCode, MarketObservation, Unit
from credit_radar.domain.provenance import (
    CollectionRun,
    CollectionStatus,
    Provenance,
    SourceId,
)


class Base(DeclarativeBase):
    pass


class MarketObservationRow(Base):
    """One collected value of one indicator.

    The unique constraint spans the value as well as the identity of the
    observation. Re-collecting an unchanged value is therefore a no-op at the
    database level, while a *changed* value for an already-recorded reference
    date inserts a new row -- a revision. Upstream series such as IPCA do get
    revised, and overwriting would erase the fact that the number changed.
    """

    __tablename__ = "market_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)

    value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    """Unconstrained ``numeric`` on purpose.

    Declaring a scale here (``Numeric(20, 8)``) would pad every stored value
    to that scale, so a rate published as "14.00" would read back as
    "14.00000000". PostgreSQL's unconstrained numeric keeps the scale it was
    given, which is what preserves the precision the source actually
    published. Never narrow this to a float type.
    """

    unit: Mapped[str] = mapped_column(String(32), nullable=False)

    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    collector: Mapped[str] = mapped_column(String(255), nullable=False)
    collector_version: Mapped[str] = mapped_column(String(32), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "indicator_code",
            "source_id",
            "reference_date",
            "value",
            name="uq_market_observation_identity_and_value",
        ),
        Index(
            "ix_market_observations_indicator_reference",
            "indicator_code",
            "reference_date",
        ),
    )

    def to_domain(self) -> MarketObservation:
        return MarketObservation(
            indicator_code=IndicatorCode(self.indicator_code),
            reference_date=self.reference_date,
            value=self.value,
            unit=Unit(self.unit),
            provenance=Provenance(
                source_id=SourceId(self.source_id),
                source_reference=self.source_reference,
                collector=self.collector,
                collector_version=self.collector_version,
                collected_at=self.collected_at,
                request_url=self.request_url,
            ),
        )

    @classmethod
    def from_domain(cls, observation: MarketObservation) -> MarketObservationRow:
        return cls(
            indicator_code=observation.indicator_code.value,
            reference_date=observation.reference_date,
            value=observation.value,
            unit=observation.unit.value,
            source_id=observation.provenance.source_id.value,
            source_reference=observation.provenance.source_reference,
            collector=observation.provenance.collector,
            collector_version=observation.provenance.collector_version,
            collected_at=observation.provenance.collected_at,
            request_url=observation.provenance.request_url,
        )


class CollectionRunRow(Base):
    """Audit record of one collection attempt."""

    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    collector: Mapped[str] = mapped_column(String(255), nullable=False)
    collector_version: Mapped[str] = mapped_column(String(32), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False)
    observation_count: Mapped[int] = mapped_column(nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Failure summary only. Must never contain credentials or personal data."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_collection_runs_source_started",
            "source_id",
            "source_reference",
            "started_at",
        ),
    )

    def to_domain(self) -> CollectionRun:
        return CollectionRun(
            source_id=SourceId(self.source_id),
            source_reference=self.source_reference,
            collector=self.collector,
            collector_version=self.collector_version,
            started_at=self.started_at,
            finished_at=self.finished_at,
            status=CollectionStatus(self.status),
            observation_count=self.observation_count,
            error_message=self.error_message,
        )

    @classmethod
    def from_domain(cls, run: CollectionRun) -> CollectionRunRow:
        return cls(
            source_id=run.source_id.value,
            source_reference=run.source_reference,
            collector=run.collector,
            collector_version=run.collector_version,
            started_at=run.started_at,
            finished_at=run.finished_at,
            status=run.status.value,
            observation_count=run.observation_count,
            error_message=run.error_message,
        )
