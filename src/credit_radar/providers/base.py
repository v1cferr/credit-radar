"""Contract shared by market-data providers."""

from __future__ import annotations

from dataclasses import dataclass

from credit_radar.domain.market import MarketObservation
from credit_radar.domain.provenance import CollectionRun


@dataclass(frozen=True)
class MarketCollectionOutcome:
    """Everything one collection attempt produced.

    Observations and the audit record travel together so a caller cannot
    persist the data while forgetting the evidence of how it was obtained.
    An empty ``observations`` tuple is meaningful when paired with the run
    status: it separates "the source had nothing" from "the fetch failed".
    """

    observations: tuple[MarketObservation, ...]
    run: CollectionRun
