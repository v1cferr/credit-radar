"""Market indicator endpoints.

Resource-oriented and generic over indicators rather than hardcoding
`/selic/`. Selic is one code among several, so the same routes already serve
IPCA and the vehicle and mortgage financing rates without new endpoints.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from credit_radar.api.dependencies import DbSession, IngestionService
from credit_radar.api.schemas import (
    CollectionRunResponse,
    IndicatorResponse,
    IndicatorSummary,
    IngestionResponse,
    MarketSummaryResponse,
    ObservationResponse,
    ObservationSeriesResponse,
)
from credit_radar.domain.market import INDICATOR_CATALOG, IndicatorCode
from credit_radar.persistence.repositories import (
    CollectionRunRepository,
    MarketObservationRepository,
)
from credit_radar.providers.bcb.sgs import SGS_MAX_LATEST_VALUES, SGS_SERIES

router = APIRouter(prefix="/market", tags=["market"])

MAX_HISTORY_POINTS = 5000


def _source_reference(indicator: IndicatorCode) -> str | None:
    series = SGS_SERIES.get(indicator)
    return f"bcdata.sgs.{series}" if series else None


@router.get("/indicators", response_model=list[IndicatorResponse])
def list_indicators() -> list[IndicatorResponse]:
    """List every indicator CreditRadar tracks."""
    return [IndicatorResponse.from_domain(i) for i in INDICATOR_CATALOG.values()]


@router.get("/summary", response_model=MarketSummaryResponse)
def market_summary(session: DbSession) -> MarketSummaryResponse:
    """Current value and collection health of every indicator.

    Serves the dashboard in a single request. An indicator with nothing
    collected yet returns a null ``latest`` so the UI can say so, instead of
    being handed a zero that would read as a real rate.
    """
    observations = MarketObservationRepository(session)
    runs = CollectionRunRepository(session)

    summaries: list[IndicatorSummary] = []
    for code, indicator in INDICATOR_CATALOG.items():
        latest = observations.latest(code)
        previous = observations.before_last_change(code) if latest else None
        reference = _source_reference(code)
        last_run = runs.last_run(reference) if reference else None
        summaries.append(
            IndicatorSummary(
                indicator=IndicatorResponse.from_domain(indicator),
                latest=ObservationResponse.from_domain(latest) if latest else None,
                previous=ObservationResponse.from_domain(previous) if previous else None,
                last_run=CollectionRunResponse.from_domain(last_run) if last_run else None,
            )
        )
    return MarketSummaryResponse(indicators=summaries)


@router.get("/indicators/{code}/observations/latest", response_model=ObservationResponse)
def latest_observation(code: IndicatorCode, session: DbSession) -> ObservationResponse:
    """Current value of one indicator."""
    latest = MarketObservationRepository(session).latest(code)
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no observations recorded for {code.value}",
        )
    return ObservationResponse.from_domain(latest)


@router.get("/indicators/{code}/observations", response_model=ObservationSeriesResponse)
def observation_history(
    code: IndicatorCode,
    session: DbSession,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_HISTORY_POINTS)] = 1000,
) -> ObservationSeriesResponse:
    """History of one indicator, one point per reference date, oldest first."""
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="'from' must not be after 'to'",
        )

    history = MarketObservationRepository(session).history(code, start=start, end=end, limit=limit)
    return ObservationSeriesResponse(
        indicator=IndicatorResponse.from_domain(INDICATOR_CATALOG[code]),
        observations=[ObservationResponse.from_domain(o) for o in history],
    )


@router.post(
    "/indicators/{code}/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_200_OK,
)
def ingest_indicator(
    code: IndicatorCode,
    service: IngestionService,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
    count: Annotated[int, Query(ge=1, le=SGS_MAX_LATEST_VALUES)] = 20,
) -> IngestionResponse:
    """Collect an indicator from its upstream source and append what is new.

    Two modes. Without ``from``/``to`` it refreshes the most recent ``count``
    points, capped at the upstream limit of 20. With a date range it
    backfills, which is the only way to load history: the "latest N" form of
    the SGS API refuses more than 20 values, while the range form is
    uncapped.

    Explicitly triggered. This only reads public market data and creates no
    financial obligation of any kind, which is why it is safe to expose as a
    plain action; nothing in CreditRadar may ever perform a financial
    operation without a human doing it themselves.
    """
    if code not in SGS_SERIES:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"no provider is implemented for {code.value}",
        )

    if start is not None and end is not None:
        if start > end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="'from' must not be after 'to'",
            )
        result = service.ingest_range(code, start=start, end=end)
    else:
        result = service.ingest_latest(code, count=count)

    return IngestionResponse(
        indicator_code=code,
        collected=result.collected,
        stored=result.stored,
        run=CollectionRunResponse.from_domain(result.run),
    )
