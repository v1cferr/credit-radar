"""Persistence behaviour, verified against a real PostgreSQL instance."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from credit_radar.domain.market import IndicatorCode, MarketObservation, Unit
from credit_radar.domain.provenance import Provenance, SourceId
from credit_radar.persistence.repositories import MarketObservationRepository

pytestmark = pytest.mark.integration


def observation(
    *,
    value: str,
    reference_date: date = date(2026, 9, 9),
    collected_at: datetime = datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
    indicator: IndicatorCode = IndicatorCode.SELIC_TARGET,
    unit: Unit = Unit.PERCENT_PER_YEAR,
) -> MarketObservation:
    return MarketObservation(
        indicator_code=indicator,
        reference_date=reference_date,
        value=value,  # type: ignore[arg-type]
        unit=unit,
        provenance=Provenance(
            source_id=SourceId.BCB_SGS,
            source_reference="bcdata.sgs.432",
            collector="credit_radar.providers.bcb.sgs",
            collector_version="1",
            collected_at=collected_at,
        ),
    )


class TestDecimalStorage:
    def test_published_scale_survives_a_database_round_trip(self, session):
        # The column is unconstrained `numeric` precisely so that "14.00"
        # does not come back as "14.00000000". A fixed scale here would
        # silently rewrite the precision the source published.
        repository = MarketObservationRepository(session)
        repository.add_all([observation(value="14.00")])
        session.flush()

        stored = repository.latest(IndicatorCode.SELIC_TARGET)

        assert stored is not None
        assert stored.value == Decimal("14.00")
        assert str(stored.value) == "14.00"

    def test_high_precision_values_are_not_truncated(self, session):
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(
                    value="0.051660",
                    indicator=IndicatorCode.IPCA_MONTHLY,
                    unit=Unit.PERCENT_PER_MONTH,
                )
            ]
        )
        session.flush()

        stored = repository.latest(IndicatorCode.IPCA_MONTHLY)

        assert stored is not None
        assert str(stored.value) == "0.051660"


class TestAppendOnlyHistory:
    def test_storing_the_same_value_twice_inserts_once(self, session):
        # Re-running a collection must be cheap and safe, otherwise a
        # scheduled collector would grow the table without adding information.
        repository = MarketObservationRepository(session)

        first = repository.add_all([observation(value="14.00")])
        second = repository.add_all([observation(value="14.00")])
        session.flush()

        assert first == 1
        assert second == 0
        assert len(repository.revisions(IndicatorCode.SELIC_TARGET, date(2026, 9, 9))) == 1

    def test_a_changed_value_is_recorded_as_a_revision(self, session):
        # Upstream series do get revised. Overwriting would erase the fact
        # that the published number changed.
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(
                    value="0.07",
                    indicator=IndicatorCode.IPCA_MONTHLY,
                    unit=Unit.PERCENT_PER_MONTH,
                    reference_date=date(2026, 7, 1),
                    collected_at=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
                )
            ]
        )
        repository.add_all(
            [
                observation(
                    value="0.09",
                    indicator=IndicatorCode.IPCA_MONTHLY,
                    unit=Unit.PERCENT_PER_MONTH,
                    reference_date=date(2026, 7, 1),
                    collected_at=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
                )
            ]
        )
        session.flush()

        revisions = repository.revisions(IndicatorCode.IPCA_MONTHLY, date(2026, 7, 1))

        assert [str(r.value) for r in revisions] == ["0.07", "0.09"]

    def test_history_returns_the_current_revision_per_reference_date(self, session):
        # A chart shows what the series says now, not every correction.
        repository = MarketObservationRepository(session)
        for value, collected in (
            ("0.07", datetime(2026, 8, 10, tzinfo=UTC)),
            ("0.09", datetime(2026, 9, 10, tzinfo=UTC)),
        ):
            repository.add_all(
                [
                    observation(
                        value=value,
                        indicator=IndicatorCode.IPCA_MONTHLY,
                        unit=Unit.PERCENT_PER_MONTH,
                        reference_date=date(2026, 7, 1),
                        collected_at=collected,
                    )
                ]
            )
        session.flush()

        history = repository.history(IndicatorCode.IPCA_MONTHLY)

        assert len(history) == 1
        assert str(history[0].value) == "0.09"

    def test_history_is_ordered_oldest_first(self, session):
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(value="14.00", reference_date=date(2026, 9, 11)),
                observation(value="15.00", reference_date=date(2026, 9, 9)),
                observation(value="14.50", reference_date=date(2026, 9, 10)),
            ]
        )
        session.flush()

        history = repository.history(IndicatorCode.SELIC_TARGET)

        assert [o.reference_date.day for o in history] == [9, 10, 11]

    def test_history_can_be_bounded_by_reference_date(self, session):
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(value="15.00", reference_date=date(2026, 9, 8)),
                observation(value="14.50", reference_date=date(2026, 9, 9)),
                observation(value="14.00", reference_date=date(2026, 9, 10)),
            ]
        )
        session.flush()

        history = repository.history(
            IndicatorCode.SELIC_TARGET, start=date(2026, 9, 9), end=date(2026, 9, 9)
        )

        assert [str(o.value) for o in history] == ["14.50"]

    def test_latest_prefers_the_newest_reference_date(self, session):
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(value="15.00", reference_date=date(2026, 9, 8)),
                observation(value="14.00", reference_date=date(2026, 9, 16)),
            ]
        )
        session.flush()

        latest = repository.latest(IndicatorCode.SELIC_TARGET)

        assert latest is not None
        assert latest.reference_date == date(2026, 9, 16)

    def test_latest_prefers_the_newest_revision_of_that_date(self, session):
        repository = MarketObservationRepository(session)
        repository.add_all(
            [observation(value="13.00", collected_at=datetime(2026, 9, 9, 8, tzinfo=UTC))]
        )
        repository.add_all(
            [observation(value="14.00", collected_at=datetime(2026, 9, 9, 18, tzinfo=UTC))]
        )
        session.flush()

        latest = repository.latest(IndicatorCode.SELIC_TARGET)

        assert latest is not None
        assert str(latest.value) == "14.00"

    def test_latest_is_none_when_nothing_was_ever_collected(self, session):
        repository = MarketObservationRepository(session)
        assert repository.latest(IndicatorCode.IGPM_MONTHLY) is None


class TestProvenanceRoundTrip:
    def test_provenance_is_stored_and_read_back_intact(self, session):
        repository = MarketObservationRepository(session)
        repository.add_all([observation(value="14.00")])
        session.flush()

        stored = repository.latest(IndicatorCode.SELIC_TARGET)

        assert stored is not None
        assert stored.provenance.source_id == SourceId.BCB_SGS
        assert stored.provenance.source_reference == "bcdata.sgs.432"
        assert stored.provenance.collector_version == "1"
        assert stored.provenance.collected_at == datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


class TestBeforeLastChange:
    """The value an indicator held before the one it holds now.

    This exists because "the previous observation" is the wrong question for
    a policy rate. The Selic target is published every business day and does
    not move between Copom decisions, so a difference against yesterday is
    almost always zero and says nothing.
    """

    def test_skips_repeated_values_to_find_the_last_movement(self, session):
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(value="13.25", reference_date=date(2026, 6, 15)),
                observation(value="13.25", reference_date=date(2026, 6, 16)),
                observation(value="14.00", reference_date=date(2026, 6, 17)),
                observation(value="14.00", reference_date=date(2026, 6, 18)),
                observation(value="14.00", reference_date=date(2026, 6, 19)),
            ]
        )
        session.flush()

        previous = repository.before_last_change(IndicatorCode.SELIC_TARGET)

        assert previous is not None
        assert previous.value == Decimal("13.25")
        # The last date the older value applied, which is when it changed.
        assert previous.reference_date == date(2026, 6, 16)

    def test_is_the_preceding_period_for_a_series_that_always_moves(self, session):
        # A monthly average rate differs every month, so the answer here is
        # simply the previous month -- which is what one would want anyway.
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(value="24.10", reference_date=date(2026, 7, 1)),
                observation(value="24.50", reference_date=date(2026, 8, 1)),
            ]
        )
        session.flush()

        previous = repository.before_last_change(IndicatorCode.SELIC_TARGET)

        assert previous is not None
        assert previous.value == Decimal("24.10")
        assert previous.reference_date == date(2026, 7, 1)

    def test_a_value_that_returned_reports_the_one_in_between(self, session):
        # 13.25 -> 13.00 -> 13.25. The current value equals an older one,
        # but what it moved from is the value in between.
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(value="13.25", reference_date=date(2026, 6, 1)),
                observation(value="13.00", reference_date=date(2026, 7, 1)),
                observation(value="13.25", reference_date=date(2026, 8, 1)),
            ]
        )
        session.flush()

        previous = repository.before_last_change(IndicatorCode.SELIC_TARGET)

        assert previous is not None
        assert previous.value == Decimal("13.00")

    def test_a_scale_change_is_not_a_rate_change(self, session):
        # "13.250" is the same rate as "13.25" published to one more
        # decimal. Treating that as movement would show "+0,000 p.p." as if
        # something had happened.
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(value="13.25", reference_date=date(2026, 6, 1)),
                observation(value="13.250", reference_date=date(2026, 7, 1)),
            ]
        )
        session.flush()

        assert repository.before_last_change(IndicatorCode.SELIC_TARGET) is None

    def test_is_none_when_the_series_has_never_moved(self, session):
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(value="13.25", reference_date=date(2026, 6, 1)),
                observation(value="13.25", reference_date=date(2026, 7, 1)),
            ]
        )
        session.flush()

        assert repository.before_last_change(IndicatorCode.SELIC_TARGET) is None

    def test_is_none_when_nothing_was_ever_collected(self, session):
        repository = MarketObservationRepository(session)

        assert repository.before_last_change(IndicatorCode.SELIC_TARGET) is None

    def test_a_correction_to_an_old_value_is_not_a_movement(self, session):
        # A revision replaces what a reference date says; it must be read
        # through the same current-revision rule as `history`, or a
        # correction would look like the rate having changed twice.
        repository = MarketObservationRepository(session)
        repository.add_all(
            [
                observation(
                    value="13.00",
                    reference_date=date(2026, 6, 1),
                    collected_at=datetime(2026, 6, 2, 12, 0, tzinfo=UTC),
                ),
                observation(value="14.00", reference_date=date(2026, 7, 1)),
            ]
        )
        session.flush()
        # June is corrected to 13.50, later than it was first collected.
        repository.add_all(
            [
                observation(
                    value="13.50",
                    reference_date=date(2026, 6, 1),
                    collected_at=datetime(2026, 6, 20, 12, 0, tzinfo=UTC),
                )
            ]
        )
        session.flush()

        previous = repository.before_last_change(IndicatorCode.SELIC_TARGET)

        assert previous is not None
        assert previous.value == Decimal("13.50")
