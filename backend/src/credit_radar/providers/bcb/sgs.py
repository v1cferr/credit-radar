"""Banco Central do Brasil, SGS time-series API.

SGS (Sistema Gerenciador de Series Temporais) publishes Brazil's official
macroeconomic and credit-market series as a plain JSON API with no
authentication. It is therefore the highest-preference integration type in
this project's acquisition strategy -- an official API -- and the right place
to validate the provider architecture before any authenticated bureau is
attempted.

Payload contract, as observed:

    [{"data": "16/09/2026", "valor": "14.00"}]

Both fields are strings. ``data`` is ``dd/MM/yyyy``. ``valor`` is a decimal
string using a dot separator, and is parsed as Decimal rather than float.

Upstream behaviours that shape this module are documented in
docs/providers/bcb-sgs.md.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final

from credit_radar.domain.market import (
    INDICATOR_CATALOG,
    IndicatorCode,
    MarketObservation,
)
from credit_radar.domain.provenance import (
    CollectionRun,
    CollectionStatus,
    Provenance,
    SourceId,
)
from credit_radar.providers.base import MarketCollectionOutcome
from credit_radar.providers.errors import (
    ProviderNoDataError,
    ProviderResponseInvalidError,
    ProviderUnavailableError,
)
from credit_radar.providers.http import HttpClient

logger = logging.getLogger(__name__)

SGS_BASE_URL: Final = "https://api.bcb.gov.br/dados/serie"

COLLECTOR: Final = "credit_radar.providers.bcb.sgs"

SGS_MAX_LATEST_VALUES: Final = 20
"""Upstream cap on the ``/dados/ultimos/{n}`` form.

The API enforces this as a business rule and rejects a larger request with
HTTP 400 and "A quantidade maxima de valores deve ser 20". The date-range
form carries no such cap -- a single request for six years of the daily
Selic series returns ~2,450 rows in well under a second -- so history and
backfill go through ``fetch_range`` and ``fetch_latest`` is only for
checking the current value.
"""

COLLECTOR_VERSION: Final = "1"
"""Version of this parser.

Bump whenever normalization changes in a way that could produce a different
value from the same upstream payload. Stored with every observation so a
normalization bug fixed later stays distinguishable from data that was
always correct.
"""

SGS_SERIES: Final[dict[IndicatorCode, str]] = {
    IndicatorCode.SELIC_TARGET: "432",
    IndicatorCode.SELIC_ANNUALIZED: "1178",
    IndicatorCode.IPCA_MONTHLY: "433",
    IndicatorCode.IGPM_MONTHLY: "189",
    IndicatorCode.VEHICLE_FINANCING_RATE_PF: "20749",
    IndicatorCode.MORTGAGE_RATE_MARKET_PF: "20772",
    IndicatorCode.MORTGAGE_RATE_REGULATED_PF: "20773",
}
"""Which upstream series backs each internal indicator.

Provider knowledge, deliberately kept out of the domain: what an indicator
means belongs to the domain catalog, while the fact that its numbers
currently come from SGS series 20772 belongs here. Every code in this table
was confirmed against the Banco Central open-data catalog rather than
inferred from a plausible-looking value.
"""


def _format_sgs_date(value: date) -> str:
    """Render a date in the ``dd/MM/yyyy`` form the SGS API expects."""
    return value.strftime("%d/%m/%Y")


def _parse_reference_date(raw: Any, *, series_code: str) -> date:
    if not isinstance(raw, str):
        raise ProviderResponseInvalidError(
            f"series {series_code}: expected a string date, got {type(raw).__name__}"
        )
    try:
        return datetime.strptime(raw, "%d/%m/%Y").date()
    except ValueError as error:
        raise ProviderResponseInvalidError(
            f"series {series_code}: date {raw!r} is not in dd/MM/yyyy form"
        ) from error


def _parse_value(raw: Any, *, series_code: str) -> Decimal | None:
    """Parse an SGS value, or return None when the row carries no measurement.

    Some series include rows whose value is blank for periods where the
    indicator was not measured. Those are skipped rather than stored as zero,
    because zero is a real rate and "not measured" is not.
    """
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    if isinstance(raw, float):
        raise ProviderResponseInvalidError(
            f"series {series_code}: value arrived as float, which loses precision"
        )
    try:
        return Decimal(str(raw))
    except InvalidOperation as error:
        raise ProviderResponseInvalidError(
            f"series {series_code}: value {raw!r} is not a decimal"
        ) from error


class BcbSgsProvider:
    """Reads market indicators from the Banco Central SGS API.

    Returns normalized domain observations. No caller outside this module
    ever sees an SGS field name, so a change in the upstream payload shape is
    contained here.
    """

    source_id: Final = SourceId.BCB_SGS

    def __init__(
        self,
        http: HttpClient,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._http = http
        self._clock = clock if clock is not None else lambda: datetime.now(UTC)

    def supported_indicators(self) -> tuple[IndicatorCode, ...]:
        return tuple(SGS_SERIES)

    def fetch_latest(self, indicator: IndicatorCode, *, count: int = 1) -> MarketCollectionOutcome:
        """Fetch the most recent ``count`` observations of an indicator.

        Raises:
            ValueError: ``count`` is outside the range the upstream API
                accepts. Requesting more is rejected rather than silently
                clamped, because a caller that wanted 90 points would
                otherwise receive 20 and treat them as the whole series.
        """
        if count < 1:
            raise ValueError("count must be at least 1")
        if count > SGS_MAX_LATEST_VALUES:
            raise ValueError(
                f"the SGS API accepts at most {SGS_MAX_LATEST_VALUES} values per "
                f"'latest' request (asked for {count}); use fetch_range for history"
            )
        series_code = self._series_code(indicator)
        url = f"{SGS_BASE_URL}/bcdata.sgs.{series_code}/dados/ultimos/{count}"
        return self._collect(indicator, url, params={"formato": "json"})

    def fetch_range(
        self, indicator: IndicatorCode, *, start: date, end: date
    ) -> MarketCollectionOutcome:
        """Fetch observations of an indicator between two reference dates."""
        if start > end:
            raise ValueError("start must not be after end")
        series_code = self._series_code(indicator)
        url = f"{SGS_BASE_URL}/bcdata.sgs.{series_code}/dados"
        return self._collect(
            indicator,
            url,
            params={
                "formato": "json",
                "dataInicial": _format_sgs_date(start),
                "dataFinal": _format_sgs_date(end),
            },
        )

    def _series_code(self, indicator: IndicatorCode) -> str:
        try:
            return SGS_SERIES[indicator]
        except KeyError as error:
            raise ValueError(
                f"indicator {indicator.value} is not available from {self.source_id.value}"
            ) from error

    def _collect(
        self, indicator: IndicatorCode, url: str, *, params: dict[str, str]
    ) -> MarketCollectionOutcome:
        series_code = SGS_SERIES[indicator]
        source_reference = f"bcdata.sgs.{series_code}"
        started_at = self._clock()

        def build_run(
            status: CollectionStatus,
            observation_count: int,
            error_message: str | None = None,
        ) -> CollectionRun:
            return CollectionRun(
                source_id=self.source_id,
                source_reference=source_reference,
                collector=COLLECTOR,
                collector_version=COLLECTOR_VERSION,
                started_at=started_at,
                finished_at=self._clock(),
                status=status,
                observation_count=observation_count,
                error_message=error_message,
            )

        try:
            payload = self._http.get_json(url, params=params)
        except ProviderNoDataError:
            # The source answered that it holds nothing for this request. A
            # fact about the series, recorded as such, not a failed run.
            logger.info("SGS series %s reported no data", series_code)
            return MarketCollectionOutcome((), build_run(CollectionStatus.NO_DATA, 0))
        except (ProviderUnavailableError, ProviderResponseInvalidError) as error:
            return MarketCollectionOutcome((), build_run(CollectionStatus.FAILED, 0, str(error)))

        try:
            observations = self._normalize(indicator, payload, url=url)
        except ProviderResponseInvalidError as error:
            return MarketCollectionOutcome((), build_run(CollectionStatus.FAILED, 0, str(error)))

        status = CollectionStatus.SUCCESS if observations else CollectionStatus.NO_DATA
        return MarketCollectionOutcome(observations, build_run(status, len(observations)))

    def _normalize(
        self, indicator: IndicatorCode, payload: Any, *, url: str
    ) -> tuple[MarketObservation, ...]:
        """Convert a raw SGS payload into domain observations."""
        series_code = SGS_SERIES[indicator]
        if not isinstance(payload, list):
            raise ProviderResponseInvalidError(
                f"series {series_code}: expected a JSON array, got {type(payload).__name__}"
            )

        unit = INDICATOR_CATALOG[indicator].unit
        provenance = Provenance(
            source_id=self.source_id,
            source_reference=f"bcdata.sgs.{series_code}",
            collector=COLLECTOR,
            collector_version=COLLECTOR_VERSION,
            collected_at=self._clock(),
            request_url=url,
        )

        observations: list[MarketObservation] = []
        for row in payload:
            if not isinstance(row, dict):
                raise ProviderResponseInvalidError(
                    f"series {series_code}: expected objects in the array, got {type(row).__name__}"
                )
            if "data" not in row or "valor" not in row:
                raise ProviderResponseInvalidError(
                    f"series {series_code}: row is missing 'data' or 'valor'"
                )

            value = _parse_value(row["valor"], series_code=series_code)
            if value is None:
                logger.debug(
                    "Skipping unmeasured row in SGS series %s at %s", series_code, row["data"]
                )
                continue

            observations.append(
                MarketObservation(
                    indicator_code=indicator,
                    reference_date=_parse_reference_date(row["data"], series_code=series_code),
                    value=value,
                    unit=unit,
                    provenance=provenance,
                )
            )

        return tuple(observations)
