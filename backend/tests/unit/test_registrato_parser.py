"""Parsing an SCR report.

Every input is the synthetic report from `tests/registrato_fixture.py`.
Nothing here comes from a real document.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from credit_radar.domain.exposure import (
    DEBT_CATEGORIES,
    CreditExposureObservation,
    ExposureCategory,
)
from credit_radar.providers.bcb.registrato import (
    COLLECTOR_VERSION,
    parse_monthly_exposure,
    to_observations,
)
from credit_radar.providers.errors import ProviderResponseInvalidError
from tests.registrato_fixture import (
    COLUMN_VALUE_X,
    MonthBlock,
    build_page,
    synthetic_report,
)


@pytest.fixture
def months():
    return parse_monthly_exposure(synthetic_report())


def by_month(months, year: int, month: int):
    return next(m for m in months if m.reference_month == date(year, month, 1))


class TestMonthDetection:
    def test_every_reference_month_is_found(self, months):
        assert [m.reference_month for m in months] == [
            date(2026, 4, 1),
            date(2026, 5, 1),
            date(2026, 6, 1),
        ]

    def test_months_come_back_oldest_first(self, months):
        assert months == sorted(months, key=lambda m: m.reference_month)

    def test_a_month_is_normalized_to_its_first_day(self, months):
        # SCR reports a monthly position; a day would invent precision the
        # source does not have.
        assert all(m.reference_month.day == 1 for m in months)

    def test_a_month_split_across_pages_is_merged(self):
        # The report splits a long month across pages, and the same month
        # appearing twice must not become two entries.
        document = {
            "source_format": "pdf",
            "page_count": 2,
            "pages": [
                build_page(1, 2, [MonthBlock("06/2026", {"em_dia": "100,00"})]),
                build_page(2, 2, [MonthBlock("06/2026", {"vencida": "50,00"})]),
            ],
        }

        months = parse_monthly_exposure(document)

        assert len(months) == 1
        assert months[0].totals[ExposureCategory.OVERDUE] == Decimal("50.00")


class TestColumnAssignment:
    """The reason word geometry is carried at all."""

    def test_amounts_go_to_the_column_they_sit_under_not_the_first_ones(self, months):
        # The row reads "Mês de referência: 06/2026 R$ 1.500,00 R$ 250,75
        # R$ 9.000,00". Flowed into text those are three amounts in a line;
        # only the x coordinate says the third is a credit LIMIT and not a
        # third kind of debt.
        june = by_month(months, 2026, 6)

        assert june.totals == {
            ExposureCategory.CURRENT: Decimal("1500.00"),
            ExposureCategory.OVERDUE: Decimal("250.75"),
            ExposureCategory.CREDIT_LIMIT: Decimal("9000.00"),
        }

    def test_a_different_month_fills_different_columns(self, months):
        # Same count of amounts, different columns. An order-based parser
        # would report these as current, overdue and pending-release.
        april = by_month(months, 2026, 4)

        assert april.totals == {
            ExposureCategory.CURRENT: Decimal("980.00"),
            ExposureCategory.PENDING_RELEASE: Decimal("3000.00"),
            ExposureCategory.CO_OBLIGATION: Decimal("45.90"),
        }

    def test_a_single_amount_is_not_assumed_to_be_the_first_column(self):
        document = {"pages": [build_page(1, 1, [MonthBlock("06/2026", {"limites": "500,00"})])]}

        months = parse_monthly_exposure(document)

        assert months[0].totals == {ExposureCategory.CREDIT_LIMIT: Decimal("500.00")}

    def test_columns_are_read_from_the_page_and_not_hardcoded(self):
        # A shifted layout must still parse. Hardcoded coordinates would be a
        # fact about one export rather than about the format.
        page = build_page(1, 1, [MonthBlock("06/2026", {"vencida": "77,00"})])
        for word in page["words"]:
            word["x0"] += 40.0
            word["x1"] += 40.0

        months = parse_monthly_exposure({"pages": [page]})

        assert months[0].totals == {ExposureCategory.OVERDUE: Decimal("77.00")}


class TestAmountParsing:
    def test_a_brazilian_amount_becomes_a_decimal(self, months):
        assert by_month(months, 2026, 6).totals[ExposureCategory.CURRENT] == Decimal("1500.00")

    def test_an_amount_without_a_thousands_separator_parses(self, months):
        assert by_month(months, 2026, 4).totals[ExposureCategory.CO_OBLIGATION] == Decimal("45.90")

    def test_amounts_are_never_floats(self, months):
        for month in months:
            for amount in month.totals.values():
                assert isinstance(amount, Decimal)


class TestTotalDebt:
    """The distinction the whole model exists for."""

    def test_a_credit_limit_is_not_counted_as_debt(self, months):
        june = by_month(months, 2026, 6)

        # 1.500,00 + 250,75, and NOT the 9.000,00 limit.
        assert june.total_debt == Decimal("1750.75")

    def test_a_co_obligation_is_not_counted_as_debt(self, months):
        # A guarantee given for someone else's borrowing.
        april = by_month(months, 2026, 4)

        assert april.total_debt == Decimal("980.00")

    def test_pending_release_is_not_counted_as_debt(self, months):
        # Contracted but not disbursed: not owed yet.
        april = by_month(months, 2026, 4)

        assert ExposureCategory.PENDING_RELEASE in april.totals
        assert april.total_debt == Decimal("980.00")

    def test_only_two_categories_count_as_debt(self):
        assert set(DEBT_CATEGORIES) == {
            ExposureCategory.CURRENT,
            ExposureCategory.OVERDUE,
        }

    def test_total_debt_is_zero_when_nothing_is_owed(self):
        document = {"pages": [build_page(1, 1, [MonthBlock("06/2026", {"limites": "500,00"})])]}

        assert parse_monthly_exposure(document)[0].total_debt == Decimal(0)


class TestObservations:
    def test_one_observation_per_month_per_category(self, months):
        observations = to_observations(months)

        assert len(observations) == sum(len(m.totals) for m in months)

    def test_a_missing_category_produces_nothing_rather_than_a_zero(self, months):
        # SCR omitting a column means it reported nothing there. A zero would
        # assert a balance of zero, which is a different claim.
        observations = to_observations(months)
        may = [o for o in observations if o.reference_month == date(2026, 5, 1)]

        assert len(may) == 1
        assert may[0].category is ExposureCategory.CURRENT

    def test_every_observation_carries_provenance(self, months):
        collected = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)

        observations = to_observations(months, collected_at=collected)

        for observation in observations:
            assert observation.provenance.source_id.value == "bcb.registrato"
            assert observation.provenance.collector_version == COLLECTOR_VERSION
            assert observation.provenance.collected_at == collected

    def test_month_totals_carry_no_institution(self, months):
        for observation in to_observations(months):
            assert observation.is_month_total
            assert observation.institution is None

    def test_is_debt_agrees_with_the_category(self, months):
        for observation in to_observations(months):
            assert observation.is_debt == (observation.category in DEBT_CATEGORIES)


class TestMalformedInput:
    def test_a_document_with_no_pages_is_refused(self):
        with pytest.raises(ProviderResponseInvalidError, match="no pages"):
            parse_monthly_exposure({"pages": []})

    def test_a_page_without_words_is_skipped_not_fatal(self):
        document = {
            "pages": [
                {"page": 1, "text": "", "tables": [], "words": []},
                build_page(2, 2, [MonthBlock("06/2026", {"em_dia": "10,00"})]),
            ]
        }

        assert len(parse_monthly_exposure(document)) == 1

    def test_a_month_row_without_a_date_is_refused(self):
        # Better to fail than to attribute amounts to the wrong month.
        page = build_page(1, 1, [MonthBlock("06/2026", {"em_dia": "10,00"})])
        for word in page["words"]:
            if word["text"] == "06/2026":
                word["text"] = "??"

        with pytest.raises(ProviderResponseInvalidError, match="MM/YYYY"):
            parse_monthly_exposure({"pages": [page]})

    def test_an_impossible_month_is_refused(self):
        page = build_page(1, 1, [MonthBlock("13/2026", {"em_dia": "10,00"})])

        with pytest.raises(ProviderResponseInvalidError, match="out of range"):
            parse_monthly_exposure({"pages": [page]})

    def test_a_page_with_no_column_band_is_skipped(self):
        # Without the band there is no way to tell which column an amount
        # belongs to, and guessing is what this parser exists to avoid.
        page = build_page(1, 1, [MonthBlock("06/2026", {"em_dia": "10,00"})])
        page["words"] = [w for w in page["words"] if w["text"] != "Coobrigações"]

        assert parse_monthly_exposure({"pages": [page]}) == []


class TestDomainInvariants:
    def test_an_amount_cannot_be_built_from_a_float(self, months):
        observation = to_observations(months)[0]

        with pytest.raises(ValueError, match="must not be built from float"):
            CreditExposureObservation(
                reference_month=date(2026, 6, 1),
                category=ExposureCategory.CURRENT,
                amount=1500.00,  # type: ignore[arg-type]
                provenance=observation.provenance,
            )

    def test_a_reference_month_must_be_the_first_of_the_month(self, months):
        observation = to_observations(months)[0]

        with pytest.raises(ValueError, match="first day of the month"):
            CreditExposureObservation(
                reference_month=date(2026, 6, 15),
                category=ExposureCategory.CURRENT,
                amount=Decimal("1.00"),
                provenance=observation.provenance,
            )

    def test_a_modality_requires_an_institution(self, months):
        # Otherwise a parser bug could produce a row that looks like detail
        # and aggregates like a total.
        observation = to_observations(months)[0]

        with pytest.raises(ValueError, match="modality requires an institution"):
            CreditExposureObservation(
                reference_month=date(2026, 6, 1),
                category=ExposureCategory.CURRENT,
                amount=Decimal("1.00"),
                modality="Cartão de crédito",
                provenance=observation.provenance,
            )


def test_the_fixture_gives_each_column_a_distinct_position():
    # The property that makes column assignment testable at all.
    assert len(set(COLUMN_VALUE_X.values())) == len(COLUMN_VALUE_X)


class TestTheProseTrap:
    """A sentence that reads like a data row.

    The report states an empty month as "Não foram encontrados registros de
    operações de crédito em nome do cliente para o mês de referência." That
    sentence contains the phrase a naive parser looks for, so matching the
    phrase alone treats it as a malformed data row. The real report carries
    six of them, and the first run against it failed on the first one.

    The colon is what separates them: a data row is "Mês de referência: MM/YYYY".
    """

    def test_the_sentence_is_not_read_as_a_data_row(self):
        from tests.registrato_fixture import NO_OPERATIONS_SENTENCE

        page = build_page(
            1,
            1,
            [
                MonthBlock("06/2026", {"em_dia": "10,00"}),
                MonthBlock("05/2026", {}, no_operations=True),
            ],
        )
        assert NO_OPERATIONS_SENTENCE in page["text"]

        months = parse_monthly_exposure({"pages": [page]})

        assert [m.reference_month for m in months] == [
            date(2026, 5, 1),
            date(2026, 6, 1),
        ]

    def test_a_month_the_report_calls_empty_has_no_totals(self):
        # Distinct from a month nobody collected: the report asserts this one
        # was empty, and a historical series has to tell those apart.
        page = build_page(1, 1, [MonthBlock("05/2026", {}, no_operations=True)])

        months = parse_monthly_exposure({"pages": [page]})

        assert months[0].totals == {}
        assert months[0].total_debt == Decimal(0)

    def test_a_data_row_still_raises_when_it_has_no_month(self):
        # The distinction must not have made malformed data rows silent.
        page = build_page(1, 1, [MonthBlock("06/2026", {"em_dia": "10,00"})])
        for word in page["words"]:
            if word["text"] == "06/2026":
                word["text"] = "??"

        with pytest.raises(ProviderResponseInvalidError, match="MM/YYYY"):
            parse_monthly_exposure({"pages": [page]})
