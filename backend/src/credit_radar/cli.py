"""Command line entry point.

Exists so collection can be scheduled. Until now the only way to collect was
an HTTP request, and a scheduled job whose interface is a URL breaks the
first time a route is renamed. A command is also what makes the schedule
testable without standing up the API.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import UTC, date, datetime, timedelta

from credit_radar.config import get_settings
from credit_radar.credentials import (
    CREDENTIAL_SPECS,
    CredentialStore,
    secret_name,
)
from credit_radar.domain.market import INDICATOR_CATALOG, Frequency, IndicatorCode
from credit_radar.domain.provenance import CollectionStatus
from credit_radar.logging_config import configure_logging
from credit_radar.persistence.database import session_scope
from credit_radar.providers.bcb.sgs import SGS_SERIES, BcbSgsProvider
from credit_radar.providers.http import HttpClient
from credit_radar.services.market_ingestion import IngestionResult, MarketIngestionService

logger = logging.getLogger("credit_radar.collect")

LOOKBACK_DAYS: dict[Frequency, int] = {
    Frequency.DAILY: 30,
    Frequency.BUSINESS_DAILY: 30,
    Frequency.MONTHLY: 400,
}
"""How far back a routine collection re-reads, per publication frequency.

Not a fixed window, because the point of collecting on a schedule is to
capture REVISIONS and not only new points. A monthly series like IPCA is
revised after publication, so re-reading roughly thirteen months every run is
what notices a corrected figure; a daily series only needs enough overlap to
survive the machine being off for a couple of weeks.

Re-reading is close to free: an unchanged value hits the unique constraint
and stores nothing, so the cost is one request and no rows.
"""

DEFAULT_PAUSE_SECONDS = 2.0
"""Gap between indicators.

The SGS API returns transient 502s when requests arrive in rapid succession,
which is measured behaviour and not caution. Seven indicators back to back is
exactly the pattern that triggers it.
"""


def _lookback_start(indicator: IndicatorCode, today: date) -> date:
    frequency = INDICATOR_CATALOG[indicator].frequency
    return today - timedelta(days=LOOKBACK_DAYS[frequency])


def _describe(indicator: IndicatorCode, result: IngestionResult) -> str:
    return (
        f"{indicator.value}: status={result.run.status.value} "
        f"collected={result.collected} stored={result.stored}"
    )


def collect(
    indicators: list[IndicatorCode],
    *,
    start: date | None = None,
    end: date | None = None,
    quiet: bool = False,
    pause_seconds: float = DEFAULT_PAUSE_SECONDS,
    today: date | None = None,
) -> int:
    """Collect each indicator and append what is new.

    Returns:
        A process exit code. Zero when at least one indicator was collected,
        because a single provider failing is recorded as data and is visible
        in the dashboard rather than being an incident. Non-zero only when
        EVERY attempt failed, which points at the network or the
        configuration instead of at one upstream series. A unit that goes red
        for one flaky series trains you to ignore red units.
    """
    reference_day = today if today is not None else datetime.now(UTC).date()
    settings = get_settings()

    results: list[tuple[IndicatorCode, IngestionResult]] = []

    with HttpClient(timeout_seconds=settings.http_timeout_seconds) as http:
        provider = BcbSgsProvider(http)

        for position, indicator in enumerate(indicators):
            if position > 0 and pause_seconds > 0:
                time.sleep(pause_seconds)

            window_start = start if start is not None else _lookback_start(indicator, reference_day)
            window_end = end if end is not None else reference_day

            # A session per indicator, so one failure cannot roll back the
            # observations already committed for the others.
            with session_scope() as session:
                service = MarketIngestionService(provider, session)
                result = service.ingest_range(indicator, start=window_start, end=window_end)

            results.append((indicator, result))

            if result.run.status is CollectionStatus.FAILED:
                logger.warning("%s (%s)", _describe(indicator, result), result.run.error_message)
            elif result.stored or not quiet:
                # In quiet mode only a CHANGE or a failure is worth a line. A
                # journal with seven "same as yesterday" entries per day is a
                # journal nobody reads.
                logger.info("%s", _describe(indicator, result))

    failures = [r for _, r in results if r.run.status is CollectionStatus.FAILED]
    stored = sum(r.stored for _, r in results)

    if failures and len(failures) == len(results):
        logger.error("every indicator failed to collect (%d attempted)", len(results))
        return 1

    if failures:
        logger.warning("%d of %d indicators failed to collect", len(failures), len(results))

    if stored or not quiet:
        logger.info("collection finished: %d new observation(s)", stored)

    return 0


def report_credentials() -> int:
    """Report which declared credentials are present, without reading values.

    Exists so the secret wiring can be verified by the person who owns the
    secrets, without a value being printed, logged or shown to anyone. It
    reports PRESENCE only: it never displays, compares or validates a
    credential, so running it is safe anywhere the output might be read.
    """
    store = CredentialStore()

    if not CREDENTIAL_SPECS:
        print("No authenticated source declares credentials yet.")
        return 0

    incomplete = 0

    for source_id, spec in sorted(CREDENTIAL_SPECS.items(), key=lambda item: item[0].value):
        print(f"{source_id.value}")
        if spec.notes:
            print(f"  {spec.notes}")

        availability = store.availability(source_id)
        for key, present in availability.items():
            requirement = "required" if key in spec.required else "optional"
            mark = "present" if present else "MISSING"
            print(f"    [{mark:>7}] {secret_name(source_id, key)}  ({requirement})")

        if any(not availability[key] for key in spec.required):
            incomplete += 1
        print()

    if incomplete:
        print(
            f"{incomplete} source(s) cannot sign in yet. Create the missing entries in "
            "the password manager, sync them to sops, then rebuild so /run/secrets "
            "updates."
        )
        return 1

    print("Every declared credential is present.")
    return 0


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from error


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="credit-radar",
        description=(
            "CreditRadar maintenance commands. Collection only reads public "
            "market data; nothing here can create a financial obligation."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser(
        "collect",
        help="collect market indicators and append new observations",
        description=(
            "Collects each indicator over a window sized by its publication "
            "frequency, so revisions to already-recorded periods are noticed. "
            "Re-collecting an unchanged value stores nothing."
        ),
    )
    subparsers.add_parser(
        "credentials",
        help="report which declared credentials are present",
        description=(
            "Reports presence only. It never prints, logs or validates a "
            "credential value, so its output is safe to share."
        ),
    )

    collect_parser.add_argument(
        "--indicator",
        action="append",
        dest="indicators",
        choices=sorted(code.value for code in SGS_SERIES),
        help="collect only this indicator; repeatable. Defaults to all supported ones.",
    )
    collect_parser.add_argument(
        "--from",
        dest="start",
        type=_parse_date,
        help="start of an explicit window, for backfilling history.",
    )
    collect_parser.add_argument(
        "--to",
        dest="end",
        type=_parse_date,
        help="end of an explicit window.",
    )
    collect_parser.add_argument(
        "--quiet",
        action="store_true",
        help="log only changes and failures, for scheduled runs.",
    )
    collect_parser.add_argument(
        "--pause",
        dest="pause_seconds",
        type=float,
        default=DEFAULT_PAUSE_SECONDS,
        help=(
            "seconds between indicators; the upstream API returns transient "
            f"502s without a gap (default: {DEFAULT_PAUSE_SECONDS})."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    configure_logging(get_settings().log_level)

    if args.command == "credentials":
        return report_credentials()

    if args.command != "collect":  # pragma: no cover - argparse enforces this
        parser.error(f"unknown command {args.command!r}")

    if (args.start is None) != (args.end is None):
        parser.error("--from and --to must be given together")
    if args.start is not None and args.end is not None and args.start > args.end:
        parser.error("--from must not be after --to")

    indicators = (
        [IndicatorCode(value) for value in args.indicators]
        if args.indicators
        else sorted(SGS_SERIES, key=lambda code: code.value)
    )

    return collect(
        indicators,
        start=args.start,
        end=args.end,
        quiet=args.quiet,
        pause_seconds=args.pause_seconds,
    )


if __name__ == "__main__":
    sys.exit(main())
