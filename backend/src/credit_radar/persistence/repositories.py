"""Repositories for the historical record."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from credit_radar.domain.market import IndicatorCode, MarketObservation
from credit_radar.domain.provenance import CollectionRun
from credit_radar.persistence.models import CollectionRunRow, MarketObservationRow


class MarketObservationRepository:
    """Append-only storage of market observations.

    Writes never update an existing row. Storing the same value twice is
    ignored; storing a different value for a reference date already on record
    adds a revision alongside the previous one.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_all(self, observations: Sequence[MarketObservation]) -> int:
        """Store observations, ignoring ones already recorded unchanged.

        Deduplication is delegated to the unique constraint rather than to a
        read-then-write check, so concurrent collection runs cannot both pass
        the check and insert the same value twice.

        Returns:
            How many rows were actually new.
        """
        if not observations:
            return 0

        payload = [
            {
                "indicator_code": observation.indicator_code.value,
                "reference_date": observation.reference_date,
                "value": observation.value,
                "unit": observation.unit.value,
                "source_id": observation.provenance.source_id.value,
                "source_reference": observation.provenance.source_reference,
                "collector": observation.provenance.collector,
                "collector_version": observation.provenance.collector_version,
                "collected_at": observation.provenance.collected_at,
                "request_url": observation.provenance.request_url,
            }
            for observation in observations
        ]

        statement = (
            pg_insert(MarketObservationRow)
            .values(payload)
            .on_conflict_do_nothing(constraint="uq_market_observation_identity_and_value")
            .returning(MarketObservationRow.id)
        )
        return len(self._session.execute(statement).scalars().all())

    def latest(self, indicator: IndicatorCode) -> MarketObservation | None:
        """Return the current value of an indicator.

        "Current" means the newest reference date, and for that date the most
        recently collected revision.
        """
        statement = (
            select(MarketObservationRow)
            .where(MarketObservationRow.indicator_code == indicator.value)
            .order_by(
                MarketObservationRow.reference_date.desc(),
                MarketObservationRow.collected_at.desc(),
                MarketObservationRow.id.desc(),
            )
            .limit(1)
        )
        row = self._session.execute(statement).scalar_one_or_none()
        return row.to_domain() if row is not None else None

    def before_last_change(self, indicator: IndicatorCode) -> MarketObservation | None:
        """Return the observation that held the value before the current one.

        Not the previous reference date. The Selic target is published every
        business day and holds one value between Copom decisions, so the
        preceding day almost always carries the same number and a difference
        against it would read "0,00 p.p." for weeks at a time. What is worth
        showing is the value the indicator had before the one it has now,
        and when it last moved.

        For a series measured per period rather than decided -- a monthly
        average financing rate -- consecutive values essentially always
        differ, so this is the preceding month, which is what one would want
        there anyway.

        Returns None when the series has never held a different value, which
        is a real state: an indicator collected once, or one that has not
        moved since collection began, has no movement to report.
        """
        latest = self.latest(indicator)
        if latest is None:
            return None

        # One row per reference date, newest revision of each, as `history`
        # does: a correction to an old value must not register as a change.
        newest_per_date = (
            select(MarketObservationRow)
            .where(
                MarketObservationRow.indicator_code == indicator.value,
                MarketObservationRow.reference_date < latest.reference_date,
            )
            .distinct(MarketObservationRow.reference_date)
            .order_by(
                MarketObservationRow.reference_date.desc(),
                MarketObservationRow.collected_at.desc(),
                MarketObservationRow.id.desc(),
            )
            .subquery()
        )
        candidate = aliased(MarketObservationRow, newest_per_date)

        # Compared as numbers, so a value republished with a different scale
        # -- "13.25" as "13.250" -- is not mistaken for a rate change.
        statement = (
            select(candidate)
            .where(candidate.value != latest.value)
            .order_by(candidate.reference_date.desc())
            .limit(1)
        )
        row = self._session.execute(statement).scalar_one_or_none()
        return row.to_domain() if row is not None else None

    def history(
        self,
        indicator: IndicatorCode,
        *,
        start: date | None = None,
        end: date | None = None,
        limit: int | None = None,
    ) -> list[MarketObservation]:
        """Return one value per reference date, oldest first.

        Where a reference date has been revised, the most recent revision
        wins: a chart should show what the series says now, not every
        intermediate correction. Superseded revisions stay in the table and
        are reachable through ``revisions``.
        """
        # DISTINCT ON is PostgreSQL-specific, which is an accepted dependency:
        # the alternative is a window function or a correlated subquery for
        # what the database can do directly.
        newest_per_date = (
            select(MarketObservationRow)
            .where(MarketObservationRow.indicator_code == indicator.value)
            .distinct(MarketObservationRow.reference_date)
            .order_by(
                MarketObservationRow.reference_date.desc(),
                MarketObservationRow.collected_at.desc(),
                MarketObservationRow.id.desc(),
            )
        )
        if start is not None:
            newest_per_date = newest_per_date.where(MarketObservationRow.reference_date >= start)
        if end is not None:
            newest_per_date = newest_per_date.where(MarketObservationRow.reference_date <= end)
        if limit is not None:
            newest_per_date = newest_per_date.limit(limit)

        rows = self._session.execute(newest_per_date).scalars().all()
        return [row.to_domain() for row in sorted(rows, key=lambda r: r.reference_date)]

    def revisions(self, indicator: IndicatorCode, reference_date: date) -> list[MarketObservation]:
        """Return every value ever recorded for one reference date, oldest first.

        The audit trail behind ``history``: it shows whether a published
        number was later corrected.
        """
        statement = (
            select(MarketObservationRow)
            .where(
                MarketObservationRow.indicator_code == indicator.value,
                MarketObservationRow.reference_date == reference_date,
            )
            .order_by(
                MarketObservationRow.collected_at.asc(),
                MarketObservationRow.id.asc(),
            )
        )
        return [row.to_domain() for row in self._session.execute(statement).scalars().all()]


class CollectionRunRepository:
    """Append-only storage of collection attempts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, run: CollectionRun) -> None:
        self._session.add(CollectionRunRow.from_domain(run))

    def last_run(self, source_reference: str) -> CollectionRun | None:
        """Return the most recent attempt against a series, successful or not.

        Drives the "last synchronized" and provider-health indicators: a
        source whose last attempt failed must not be presented as current.
        """
        statement = (
            select(CollectionRunRow)
            .where(CollectionRunRow.source_reference == source_reference)
            .order_by(CollectionRunRow.started_at.desc(), CollectionRunRow.id.desc())
            .limit(1)
        )
        row = self._session.execute(statement).scalar_one_or_none()
        return row.to_domain() if row is not None else None
