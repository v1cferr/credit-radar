"""Collecting market observations and recording them."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from credit_radar.domain.market import IndicatorCode
from credit_radar.domain.provenance import CollectionRun, CollectionStatus
from credit_radar.persistence.repositories import (
    CollectionRunRepository,
    MarketObservationRepository,
)
from credit_radar.providers.base import MarketCollectionOutcome
from credit_radar.providers.bcb.sgs import BcbSgsProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    """What one ingestion produced."""

    run: CollectionRun

    collected: int
    """Observations the provider returned."""

    stored: int
    """Rows that were actually new.

    Lower than ``collected`` when values were already on record. Re-running an
    ingestion is therefore safe and cheap, which is what makes a scheduled
    collector viable.
    """

    @property
    def succeeded(self) -> bool:
        return self.run.status is not CollectionStatus.FAILED


class MarketIngestionService:
    """Fetches market indicators and appends them to the historical record.

    The audit run is written whatever the outcome, including failures, and is
    committed with the observations in a single transaction so the record and
    its evidence cannot diverge.
    """

    def __init__(self, provider: BcbSgsProvider, session: Session) -> None:
        self._provider = provider
        self._observations = MarketObservationRepository(session)
        self._runs = CollectionRunRepository(session)

    def ingest_latest(self, indicator: IndicatorCode, *, count: int = 1) -> IngestionResult:
        return self._store(self._provider.fetch_latest(indicator, count=count))

    def ingest_range(self, indicator: IndicatorCode, *, start: date, end: date) -> IngestionResult:
        return self._store(self._provider.fetch_range(indicator, start=start, end=end))

    def _store(self, outcome: MarketCollectionOutcome) -> IngestionResult:
        self._runs.add(outcome.run)
        stored = self._observations.add_all(outcome.observations)

        if outcome.run.status is CollectionStatus.FAILED:
            logger.warning(
                "Collection from %s failed: %s",
                outcome.run.source_reference,
                outcome.run.error_message,
            )

        return IngestionResult(
            run=outcome.run,
            collected=len(outcome.observations),
            stored=stored,
        )
