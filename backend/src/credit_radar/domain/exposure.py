"""Credit exposure: what the financial system reports under a CPF.

Banco Central's SCR records, per month, what each institution has reported
about someone's credit. The report presents five columns, and the most
important thing this module encodes is that **they are not the same kind of
number and must not be added together**.

    Em dia              money owed, not overdue
    Vencida             money owed, overdue
    Crédito a liberar   contracted, NOT yet disbursed
    Coobrigações        a guarantee given for someone ELSE's debt
    Limites de crédito  available credit, not debt at all

Summing all five would report a credit limit as a debt and someone else's
loan as your own. Only the first two are money owed, which is why that is a
property of the category and not a comment.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from credit_radar.domain.provenance import Provenance


class ExposureCategory(StrEnum):
    """One of the five columns SCR reports."""

    CURRENT = "current"
    """"Em dia": owed and not overdue. Overdue by up to 14 days still counts
    as current in SCR's own definition, which is the report's rule and not
    this project's."""

    OVERDUE = "overdue"
    """"Vencida": owed and more than 14 days late."""

    PENDING_RELEASE = "pending_release"
    """"Crédito a liberar": contracted but not disbursed. Not owed yet, and
    counting it as debt would overstate the position; ignoring it entirely
    would miss a commitment already made."""

    CO_OBLIGATION = "co_obligation"
    """"Coobrigações": a guarantee, aval or fiança given for someone else's
    debt. A real liability if they default, and NOT money this person
    borrowed."""

    CREDIT_LIMIT = "credit_limit"
    """"Limites de crédito": available credit. Not debt. Relevant to
    utilisation, never to how much is owed."""


DEBT_CATEGORIES: frozenset[ExposureCategory] = frozenset(
    {ExposureCategory.CURRENT, ExposureCategory.OVERDUE}
)
"""The only two categories that are money this person owes.

Named so that "total debt" has one definition in the codebase instead of
being re-derived, differently, at each call site.
"""


class CreditExposureObservation(BaseModel):
    """One amount, for one month, in one category, at one level of detail."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_month: date
    """The month the amount describes, normalized to its first day.

    A month and not a date: SCR reports a monthly position, and pretending to
    a day would invent precision the source does not have.
    """

    category: ExposureCategory
    amount: Decimal

    institution: str | None = None
    """The reporting institution, or None for the month's total across all of
    them. Both are stated by the report, and keeping both is what allows the
    detail to be checked against the total."""

    modality: str | None = None
    """SCR's own operation type, such as "Cartão de crédito" or "Crédito
    pessoal - sem consignação". Only meaningful with an institution."""

    provenance: Provenance

    @field_validator("amount", mode="before")
    @classmethod
    def _reject_float(cls, value: Any) -> Any:
        """Refuse float input for a monetary value.

        The same rule as market observations, for the same reason: these
        amounts are compared and summed to answer how much is owed.
        """
        if isinstance(value, float):
            raise ValueError(
                "monetary values must not be built from float; pass str, int or Decimal"
            )
        return value

    @field_validator("reference_month")
    @classmethod
    def _must_be_first_of_month(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError(f"reference_month must be the first day of the month, got {value}")
        return value

    @model_validator(mode="after")
    def _modality_requires_an_institution(self) -> CreditExposureObservation:
        """A modality without an institution has nothing to belong to.

        The report never states one that way, so allowing it here would let a
        parser bug produce a row that looks like detail and aggregates like a
        total.
        """
        if self.modality is not None and self.institution is None:
            raise ValueError("modality requires an institution")
        return self

    @property
    def is_month_total(self) -> bool:
        """Whether this is the month's total rather than one operation."""
        return self.institution is None

    @property
    def is_debt(self) -> bool:
        """Whether this amount is money this person owes."""
        return self.category in DEBT_CATEGORIES


class MonthlyExposure(BaseModel):
    """A month's totals, as the report states them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_month: date
    totals: dict[ExposureCategory, Decimal] = Field(default_factory=dict)

    @property
    def total_debt(self) -> Decimal:
        """Money owed in this month: current plus overdue, and nothing else.

        Deliberately not the sum of every column. A credit limit is not a
        debt and a co-obligation is not this person's borrowing.
        """
        return sum(
            (self.totals.get(category, Decimal(0)) for category in DEBT_CATEGORIES),
            Decimal(0),
        )
