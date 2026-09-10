"""A synthetic Registrato SCR report, built in code rather than stored as JSON.

Code and not a data file, deliberately. The geometry below IS the format, and
a reviewer can read sixty lines of construction far more easily than ten
kilobytes of coordinates. It also cannot go stale against the builder that
produced it, and there is no file for a broad `git add` to sweep into a
public repository.

Nothing here comes from a real report. The column positions are measured
format knowledge (docs/providers/registrato.md); every institution, modality
and amount is invented.

**Each column gets a DISTINCT amount**, which is the reason a synthetic
fixture is a better test than one derived from a real document: redaction
replaces every amount with the same placeholder, so a real-derived fixture
cannot verify that the parser assigns an amount to the right column. Here it
can.
"""

from __future__ import annotations

from typing import Any

# Measured from a real report. Header x and the x of the value beneath it.
COLUMN_HEADER_X: dict[str, float] = {
    "em_dia": 322.5,
    "vencida": 408.0,
    "a_liberar": 564.9,
    "coobrigacoes": 620.0,
    "limites": 783.0,
}

COLUMN_VALUE_X: dict[str, float] = {
    "em_dia": 326.2,
    "vencida": 432.2,
    "a_liberar": 568.2,
    "coobrigacoes": 624.2,
    "limites": 750.2,
}

PAGE_TITLE = "Relatório de Empréstimos e Financiamentos (SCR)"


def _word(text: str, x: float, top: float) -> dict[str, Any]:
    return {
        "text": text,
        "x0": round(x, 1),
        "x1": round(x + len(text) * 5.5, 1),
        "top": round(top, 1),
    }


def _column_band(top: float) -> list[dict[str, Any]]:
    """The header row that names the five exposure columns."""
    return [
        _word("Em", COLUMN_HEADER_X["em_dia"] - 18, top),
        _word("dia", COLUMN_HEADER_X["em_dia"], top),
        _word("Vencida", COLUMN_HEADER_X["vencida"], top),
        _word("Crédito", COLUMN_HEADER_X["a_liberar"] - 52, top),
        _word("a", COLUMN_HEADER_X["a_liberar"] - 8, top),
        _word("liberar", COLUMN_HEADER_X["a_liberar"], top),
        _word("Coobrigações", COLUMN_HEADER_X["coobrigacoes"], top),
        _word("Limites", COLUMN_HEADER_X["limites"] - 62, top),
        _word("de", COLUMN_HEADER_X["limites"] - 18, top),
        _word("crédito", COLUMN_HEADER_X["limites"], top),
    ]


def _amount(value: str, column: str, top: float) -> list[dict[str, Any]]:
    return [
        _word("R$", COLUMN_VALUE_X[column] - 14, top),
        _word(value, COLUMN_VALUE_X[column], top),
    ]


NO_OPERATIONS_SENTENCE = (
    "Não foram encontrados registros de operações de crédito em nome do "
    "cliente para o mês de referência."
)
"""How the real report states that a month held nothing.

Reproduced because it is a trap in the format rather than a detail: the
sentence contains the words "mês de referência", so a parser that looks for
that phrase alone reads it as a malformed data row. The real report carries
six of them.
"""


class MonthBlock:
    """One reference month: its totals, and the operations under it."""

    def __init__(
        self,
        month: str,
        totals: dict[str, str],
        operations: list[tuple[str, str, str, str]] | None = None,
        *,
        no_operations: bool = False,
    ) -> None:
        self.month = month
        self.totals = totals
        # (institution, modality, column, amount)
        self.operations = operations or []
        self.no_operations = no_operations


def build_page(number: int, total: int, blocks: list[MonthBlock]) -> dict[str, Any]:
    words: list[dict[str, Any]] = []
    lines: list[str] = []
    top = 40.0

    for text in (
        PAGE_TITLE,
        f"Página {number} de {total}",
        "Nome: NOME SINTETICO DE TESTE",
        "CPF/CNPJ: 000.000.000-00",
    ):
        words.append(_word(text, 30.0, top))
        lines.append(text)
        top += 14

    lines.append("Dívidas Outros compromissos financeiros")
    lines.append("Instituição")
    lines.append("Em dia Vencida Crédito a liberar Coobrigações Limites de crédito")
    words += _column_band(top)
    top += 20

    for block in blocks:
        row = [
            _word("Mês", 30.0, top),
            _word("de", 51.1, top),
            _word("referência:", 64.9, top),
            _word(block.month, 116.1, top),
        ]
        text = f"Mês de referência: {block.month}"
        # Sorted by x so the words appear in reading order, as extraction
        # would produce them. The parser must NOT rely on that order.
        for column in sorted(block.totals, key=lambda c: COLUMN_VALUE_X[c]):
            row += _amount(block.totals[column], column, top)
            text += f" R$ {block.totals[column]}"
        words += row
        lines.append(text)
        top += 18

        if block.no_operations:
            words.append(_word(NO_OPERATIONS_SENTENCE, 30.0, top))
            lines.append(NO_OPERATIONS_SENTENCE)
            top += 16

        for institution, modality, column, value in block.operations:
            words.append(_word(institution, 30.0, top))
            lines.append(institution)
            top += 14
            words.append(_word(modality, 40.0, top))
            words += _amount(value, column, top)
            lines.append(f"{modality} R$ {value}")
            top += 16

    return {"page": number, "text": "\n".join(lines), "tables": [], "words": words}


def synthetic_report() -> dict[str, Any]:
    """A two-page, three-month synthetic SCR report.

    Small enough to read in full, and shaped so every parser behaviour that
    matters is exercised: a month with three columns filled, a month with
    one, a month whose filled columns are NOT the same ones, and amounts
    that differ per column so a mis-assignment is visible.
    """
    pages = [
        build_page(
            1,
            2,
            [
                MonthBlock(
                    "06/2026",
                    {"em_dia": "1.500,00", "vencida": "250,75", "limites": "9.000,00"},
                    [
                        (
                            "BANCO SINTETICO UM S.A.",
                            "Cartão de crédito - compra à vista",
                            "em_dia",
                            "1.200,00",
                        ),
                        (
                            "BANCO SINTETICO UM S.A.",
                            "Crédito pessoal - sem consignação",
                            "vencida",
                            "250,75",
                        ),
                    ],
                ),
                MonthBlock(
                    "05/2026",
                    {"em_dia": "1.480,10"},
                    [
                        (
                            "BANCO SINTETICO UM S.A.",
                            "Cartão de crédito - compra à vista",
                            "em_dia",
                            "1.480,10",
                        )
                    ],
                ),
            ],
        ),
        build_page(
            2,
            2,
            [
                MonthBlock(
                    "04/2026",
                    # Different columns from the other months on purpose.
                    {"em_dia": "980,00", "a_liberar": "3.000,00", "coobrigacoes": "45,90"},
                    [
                        (
                            "FINANCEIRA SINTETICA DOIS S.A.",
                            "Aquisição de veículos",
                            "em_dia",
                            "980,00",
                        )
                    ],
                ),
            ],
        ),
    ]
    return {"source_format": "pdf", "page_count": len(pages), "pages": pages}
