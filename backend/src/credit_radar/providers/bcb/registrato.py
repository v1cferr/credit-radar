"""Parsing a Banco Central Registrato SCR report.

The report is not automated: gov.br gates every sign-in path behind invisible
hCaptcha, so the account holder exports the PDF themselves and this parses
what they exported. See docs/providers/registrato.md.

Input is the structure `scripts/redact_capture.py` produces: pages carrying
text and positioned words. Word positions are load-bearing, not a
convenience. A month line reads

    Mês de referência: 03/2026   R$ 1.500,00   R$ 250,75   R$ 9.000,00

and those three amounts are NOT the first three columns. They could be
current, overdue and credit limit, or current, pending-release and
co-obligation. Flowed into text there is no way to tell a balance that is
current from one that is overdue, which in a report about debt is the entire
distinction. The x coordinate is what decides.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final

from credit_radar.domain.exposure import (
    CreditExposureObservation,
    ExposureCategory,
    MonthlyExposure,
)
from credit_radar.domain.provenance import Provenance, SourceId
from credit_radar.providers.errors import ProviderResponseInvalidError

logger = logging.getLogger(__name__)

SOURCE_ID: Final = SourceId.BCB_REGISTRATO
COLLECTOR: Final = "credit_radar.providers.bcb.registrato"
COLLECTOR_VERSION: Final = "1"

# The COLON is what distinguishes a data row from prose. The report also
# writes the phrase in a sentence, "...para o mes de referencia.", on months
# with no operations, and matching the phrase alone treated six of those as
# malformed data rows.
MONTH_ROW_LABEL = re.compile(r"Mês\s+de\s+referência\s*:", re.IGNORECASE)

NO_OPERATIONS = re.compile(r"não\s+foram\s+encontrados\s+registros", re.IGNORECASE)
"""The report's own way of saying a month held no credit operations.

Recognised rather than ignored: a month the report states was empty is an
assertion that exposure was zero, which is different from a month nobody
collected. A historical series has to tell those apart.
"""
MONTH_VALUE = re.compile(r"\b(\d{2})/(\d{4})\b")
AMOUNT = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$")

ROW_TOLERANCE: Final = 3.0
"""How far apart two words may sit vertically and still be one row.

Extraction reports a fractional `top` per word, and words on a line are not
pixel-identical. Three points is wider than that jitter and far narrower than
a line height.
"""

COLUMN_MARKERS: Final[dict[ExposureCategory, str]] = {
    ExposureCategory.CURRENT: "dia",
    ExposureCategory.OVERDUE: "vencida",
    ExposureCategory.PENDING_RELEASE: "liberar",
    ExposureCategory.CO_OBLIGATION: "coobrigações",
    ExposureCategory.CREDIT_LIMIT: "crédito",
}
"""The last word of each column heading, which is where the column sits.

The headings are "Em dia", "Vencida", "Crédito a liberar", "Coobrigações" and
"Limites de crédito"; matching the final word puts the anchor under the
column rather than at the start of a phrase.

Read from the report itself rather than hardcoded as coordinates: a measured
x would be a fact about one export, and this is a fact about the layout.
"""

HEADER_REQUIRED: Final = frozenset({"vencida", "coobrigações"})
"""Words that identify the column band and appear nowhere else in the report.

"crédito" and "dia" occur throughout the modality names, so a band found by
those alone would sometimes be a row of operations.
"""


def _normalize(token: str) -> str:
    return token.strip().strip(":.,").casefold()


def _rows(words: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group words into visual rows, each sorted left to right."""
    rows: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda w: (float(w["top"]), float(w["x0"]))):
        top = float(word["top"])
        if rows and abs(float(rows[-1][0]["top"]) - top) <= ROW_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: float(w["x0"])) for row in rows]


def _find_columns(rows: Iterable[list[dict[str, Any]]]) -> dict[ExposureCategory, float]:
    """Locate each exposure column by reading the page's own header band."""
    for row in rows:
        tokens = {_normalize(word["text"]) for word in row}
        if not tokens >= HEADER_REQUIRED:
            continue

        columns: dict[ExposureCategory, float] = {}
        for category, marker in COLUMN_MARKERS.items():
            matches = [w for w in row if _normalize(w["text"]) == marker]
            if matches:
                # The rightmost, because "crédito" appears in the band twice:
                # in "Crédito a liberar" and in "Limites de crédito".
                columns[category] = float(max(matches, key=lambda w: float(w["x0"]))["x0"])
        return columns
    return {}


def _parse_amount(token: str) -> Decimal:
    """Parse a Brazilian amount into Decimal, keeping its published scale."""
    try:
        return Decimal(token.replace(".", "").replace(",", "."))
    except InvalidOperation as error:
        raise ProviderResponseInvalidError(f"{token!r} is not an amount") from error


def _assign_column(x: float, columns: dict[ExposureCategory, float]) -> ExposureCategory | None:
    """Return the column an amount at this x belongs to.

    Nearest anchor wins. Values are right-aligned under their heading and can
    sit either side of its start, so distance is the only reliable test; an
    "is it past this x" rule mis-assigns a wide value to the column before it.
    """
    if not columns:
        return None
    category, distance = min(
        ((c, abs(x - anchor)) for c, anchor in columns.items()), key=lambda pair: pair[1]
    )
    # Columns in this report are more than 50 points apart, so anything
    # further than that is not an amount belonging to a column.
    return category if distance <= 90.0 else None


def _month_from(row: Sequence[dict[str, Any]]) -> date | None:
    """Return the month a data row describes, or None if it is not one.

    Prose that merely mentions the phrase returns None. A row that IS a
    data row but carries no month raises, because attributing amounts to
    the wrong month is worse than failing.
    """
    text = " ".join(str(word["text"]) for word in row)
    if not MONTH_ROW_LABEL.search(text):
        return None
    match = MONTH_VALUE.search(text)
    if not match:
        raise ProviderResponseInvalidError("a reference-month row carried no MM/YYYY value")
    month, year = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise ProviderResponseInvalidError(f"month {month} is out of range")
    return date(year, month, 1)


def parse_monthly_exposure(document: dict[str, Any]) -> list[MonthlyExposure]:
    """Extract each reference month's totals from an extracted report.

    Returns one entry per month found, oldest first. A month appearing on
    more than one page is merged rather than duplicated, because the report
    splits a long month across pages.

    Raises:
        ProviderResponseInvalidError: the document is not shaped like an
            extracted report, or a month row is malformed.
    """
    pages = document.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ProviderResponseInvalidError("the document has no pages")

    merged: dict[date, dict[ExposureCategory, Decimal]] = {}

    for page in pages:
        words = page.get("words")
        if not isinstance(words, list) or not words:
            continue

        rows = _rows(words)
        columns = _find_columns(rows)
        if not columns:
            logger.debug("page %s has no column band", page.get("page"))
            continue

        for row in rows:
            month = _month_from(row)
            if month is None:
                continue

            totals = merged.setdefault(month, {})
            for word in row:
                token = str(word["text"]).strip()
                if not AMOUNT.match(token):
                    continue
                category = _assign_column(float(word["x0"]), columns)
                if category is None:
                    logger.warning("an amount on the %s row matched no column", month.isoformat())
                    continue
                totals[category] = _parse_amount(token)

    return [
        MonthlyExposure(reference_month=month, totals=totals)
        for month, totals in sorted(merged.items())
    ]


def to_observations(
    months: Sequence[MonthlyExposure], *, collected_at: datetime | None = None
) -> list[CreditExposureObservation]:
    """Turn parsed months into domain observations with provenance.

    One observation per month per category. A month with no amount in a
    category produces nothing, rather than a zero: SCR omitting a column
    means it reported nothing there, and a zero would assert a balance of
    zero.
    """
    provenance = Provenance(
        source_id=SOURCE_ID,
        source_reference="registrato.scr",
        collector=COLLECTOR,
        collector_version=COLLECTOR_VERSION,
        collected_at=collected_at if collected_at is not None else datetime.now(UTC),
    )

    return [
        CreditExposureObservation(
            reference_month=month.reference_month,
            category=category,
            amount=amount,
            provenance=provenance,
        )
        for month in months
        for category, amount in sorted(month.totals.items(), key=lambda pair: pair[0].value)
    ]
