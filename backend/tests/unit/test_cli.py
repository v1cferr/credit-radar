"""Argument handling and window sizing for the collection command."""

from __future__ import annotations

from datetime import date

import pytest

from credit_radar.cli import LOOKBACK_DAYS, _build_parser, _lookback_start
from credit_radar.domain.market import INDICATOR_CATALOG, Frequency, IndicatorCode
from credit_radar.providers.bcb.sgs import SGS_SERIES


class TestLookbackWindow:
    def test_every_frequency_has_a_window(self):
        # A missing entry would raise at collection time, on a schedule,
        # where nobody is watching.
        assert set(LOOKBACK_DAYS) == set(Frequency)

    def test_a_monthly_series_looks_back_far_enough_to_catch_revisions(self):
        # The reason for collecting on a schedule is revisions, not just new
        # points. IPCA is revised after publication, so a window of a few
        # days would only ever see the newest month.
        start = _lookback_start(IndicatorCode.IPCA_MONTHLY, date(2026, 9, 10))

        assert (date(2026, 9, 10) - start).days >= 365

    def test_a_daily_series_looks_back_enough_to_survive_an_outage(self):
        start = _lookback_start(IndicatorCode.SELIC_TARGET, date(2026, 9, 10))

        span = (date(2026, 9, 10) - start).days
        assert 14 <= span <= 60

    def test_the_window_follows_the_catalog_and_not_the_indicator_name(self):
        for code, indicator in INDICATOR_CATALOG.items():
            if code not in SGS_SERIES:
                continue
            expected = LOOKBACK_DAYS[indicator.frequency]
            start = _lookback_start(code, date(2026, 9, 10))
            assert (date(2026, 9, 10) - start).days == expected


class TestArgumentParsing:
    def test_collect_defaults_to_no_explicit_window(self):
        args = _build_parser().parse_args(["collect"])

        assert args.start is None
        assert args.end is None
        assert args.indicators is None
        assert args.quiet is False

    def test_indicator_is_repeatable(self):
        args = _build_parser().parse_args(
            ["collect", "--indicator", "SELIC_TARGET", "--indicator", "IPCA_MONTHLY"]
        )

        assert args.indicators == ["SELIC_TARGET", "IPCA_MONTHLY"]

    def test_only_indicators_a_provider_supports_are_accepted(self):
        # Offering a code with no provider would produce a run that always
        # fails, on a schedule.
        with pytest.raises(SystemExit):
            _build_parser().parse_args(["collect", "--indicator", "NOT_AN_INDICATOR"])

    def test_dates_must_be_iso(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args(["collect", "--from", "10/09/2026", "--to", "2026-09-10"])

    def test_a_pause_between_indicators_is_on_by_default(self):
        # The upstream API returns transient 502s on rapid successive
        # requests, and the batch is seven indicators.
        args = _build_parser().parse_args(["collect"])

        assert args.pause_seconds > 0

    def test_a_command_is_required(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args([])
