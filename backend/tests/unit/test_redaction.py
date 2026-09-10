"""The redaction tool, tested with synthetic documents only.

This tool is what stands between a real credit report and a committed
fixture, so what it misses is what leaks. Every input here is invented; none
of it resembles a real person's data.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "redact_capture.py"


def load_module():
    """Import the script by path: scripts/ is not an installed package."""
    spec = importlib.util.spec_from_file_location("redact_capture", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def redact():
    return load_module()


@pytest.fixture
def redactor(redact):
    return redact.Redactor()


class TestIdentifiers:
    def test_a_formatted_cpf_is_replaced(self, redactor):
        assert "000.000.000-00" in redactor.text("CPF 529.982.247-25 consultado")

    def test_a_bare_cpf_is_replaced(self, redactor):
        # Reports mix both forms, sometimes in the same document.
        assert "00000000000" in redactor.text("cpf=52998224725")

    def test_a_formatted_cnpj_is_replaced(self, redactor):
        assert "00.000.000/0000-00" in redactor.text("CNPJ 45.997.418/0001-53")

    def test_a_cnpj_is_not_eaten_by_the_cpf_rule(self, redactor):
        # A 14-digit number contains 11 digits. Ordering the patterns wrong
        # would leave three stray digits behind and look like it worked.
        result = redactor.text("45997418000153")
        assert result == "00000000000000"

    def test_an_email_is_replaced(self, redactor):
        assert "synthetic@example.invalid" in redactor.text("contato: alguem@exemplo.com")

    def test_a_phone_is_replaced(self, redactor):
        assert "(00) 00000-0000" in redactor.text("tel (16) 98888-7777")

    def test_replacements_keep_the_original_length(self, redactor):
        # A fixed-width or column-aligned report would stop parsing if a
        # replacement changed the field width.
        original = "529.982.247-25"
        assert len(redactor.text(original)) == len(original)


class TestAmounts:
    def test_a_brazilian_amount_is_replaced(self, redactor):
        # Not an identifier, but a committed fixture of real balances is
        # still someone's financial position, and a parser only needs shape.
        assert "1.234,56" in redactor.text("saldo devedor 48.750,33")

    def test_a_plain_number_is_left_alone(self, redactor):
        # Changing every number would destroy the structure the parser is
        # being written against.
        assert redactor.text("parcelas: 48") == "parcelas: 48"


class TestPersonalFields:
    def test_a_name_field_is_replaced_by_position(self, redact, redactor):
        # A name cannot be matched by a pattern, so it is matched by the
        # field it sits in.
        result = redactor.walk({"titular": "Alguem Da Silva Sauro"})

        assert result["titular"] == redact.SYNTHETIC_NAME
        assert "Sauro" not in json.dumps(result)

    def test_a_birth_date_field_is_replaced(self, redact, redactor):
        result = redactor.walk({"dataNascimento": "1988-04-17"})

        assert result["dataNascimento"] == redact.SYNTHETIC_DATE

    def test_the_name_replacement_does_not_impersonate_a_person(self, redact):
        # A `nome` can hold an institution, and over-redaction is the safe
        # direction, but the marker must read as redacted rather than as
        # somebody's name sitting in an institution slot.
        assert redact.SYNTHETIC_NAME.isupper()

    def test_nesting_and_key_order_survive(self, redactor):
        document = {
            "titular": "Alguem",
            "instituicoes": [{"nome": "BANCO X", "operacoes": [{"parcelas": 12}]}],
        }

        result = redactor.walk(document)

        assert list(result) == ["titular", "instituicoes"]
        assert result["instituicoes"][0]["operacoes"][0]["parcelas"] == 12

    def test_an_unknown_field_holding_an_identifier_is_still_caught(self, redactor):
        # Belt and braces: the field name is unrecognised, but the pattern
        # rules still run over the value.
        result = redactor.walk({"campoDesconhecido": "doc 529.982.247-25"})

        assert "529.982.247-25" not in json.dumps(result)


class TestReporting:
    def test_it_counts_what_it_replaced(self, redactor):
        redactor.walk({"titular": "Alguem", "obs": "CPF 529.982.247-25"})

        assert redactor.counts["cpf"] == 1
        assert redactor.counts["field:titular"] == 1

    def test_nothing_matched_is_distinguishable_from_something_matched(self, redactor):
        redactor.walk({"modalidade": "Financiamento de veiculo"})

        # An empty counter is what tells the reviewer the rules recognised
        # nothing, which may mean the document is clean or may mean the rules
        # do not fit its shape.
        assert redactor.counts == {}


class TestBinaryRefusal:
    """Formats whose text the rules cannot see must be refused, not passed."""

    def test_a_pdf_is_refused_without_an_explicit_opt_in(self, redact, tmp_path):
        # The dangerous case. A PDF keeps its text in compressed streams, so
        # these rules find nothing and would report "nothing matched" over a
        # document that still holds a CPF. A false clean bill of health on a
        # credit report is worse than no tool, because the output looks
        # reviewed.
        source = tmp_path / "report.pdf"
        source.write_bytes(b"%PDF-1.7\n binary junk \x00\x01")

        with pytest.raises(SystemExit):
            redact._reject_binary(source, pdf_allowed=False)

    def test_a_pdf_is_allowed_when_extraction_is_requested(self, redact, tmp_path):
        # --pdf is the opt-in: extraction can miss text that redaction then
        # never sees, so it must be asked for rather than assumed.
        source = tmp_path / "report.pdf"
        source.write_bytes(b"%PDF-1.7\n")

        redact._reject_binary(source, pdf_allowed=True)  # must not raise

    def test_a_zip_or_xlsx_is_refused(self, redact, tmp_path):
        source = tmp_path / "report.xlsx"
        source.write_bytes(b"PK\x03\x04 rest")

        with pytest.raises(SystemExit):
            redact._reject_binary(source, pdf_allowed=True)

    def test_plain_text_passes(self, redact, tmp_path):
        source = tmp_path / "report.csv"
        source.write_text("cpf;valor\n529.982.247-25;1.000,00\n", encoding="utf-8")

        redact._reject_binary(source, pdf_allowed=False)  # must not raise

    def test_json_passes(self, redact, tmp_path):
        source = tmp_path / "report.json"
        source.write_text('{"cpf": "529.982.247-25"}', encoding="utf-8")

        redact._reject_binary(source, pdf_allowed=False)  # must not raise

    def test_every_refused_signature_is_documented(self, redact):
        # A signature with no label would produce a refusal that does not say
        # what the file was or what to do instead.
        for signature, label in redact.BINARY_SIGNATURES.items():
            assert isinstance(signature, bytes)
            assert label


class TestLabelledValuesInFreeText:
    """The gap that PDF extraction exposed.

    Field-name rules only fire on a JSON key. Extracted PDF text has no keys:
    "Titular: Fulano De Teste" is one string, so a name and a birth date went
    straight through while the tool reported success. That is the most
    dangerous shape a redaction failure can take, because the output looks
    reviewed.
    """

    def test_a_labelled_name_is_redacted(self, redact, redactor):
        result = redactor.text("Titular: Alguem Da Silva Sauro")

        assert "Sauro" not in result
        assert result.startswith("Titular: ")

    def test_a_labelled_birth_date_is_redacted(self, redact, redactor):
        result = redactor.text("Data de nascimento: 17/04/1988")

        assert "17/04/1988" not in result

    def test_a_structural_date_is_preserved(self, redactor):
        # The distinction the label carries. A report's base period and an
        # instalment due date are the format a parser is written against;
        # only the label separates them from a birth date, which is why there
        # is no general date rule.
        text = "Data base: 06/2026 Gerado em: 04/08/2026"

        assert redactor.text(text) == text

    def test_the_label_itself_survives(self, redactor):
        # A parser needs to find the field; only its value is personal.
        result = redactor.text("Nome completo: Alguem")

        assert "Nome completo:" in result

    def test_it_matches_per_line_and_not_across_lines(self, redactor):
        result = redactor.text("Titular: Alguem\nModalidade: Credito pessoal")

        assert "Alguem" not in result
        assert "Credito pessoal" in result

    def test_an_unlabelled_capitalised_phrase_is_left_alone(self, redactor):
        # An institution name is not personal, and guessing at names by shape
        # would destroy the very fields the parser needs.
        text = "BANCO EXEMPLO S.A. Aquisicao de veiculos"

        assert redactor.text(text) == text


class TestPersonalTableColumns:
    def test_a_column_named_by_its_header_is_redacted(self, redact, redactor):
        # A cell holding a name carries no label of its own: only the header
        # above it says what it is.
        rows = [
            ["Titular dos dados", "Modalidade", "Saldo"],
            ["VICTOR SOBRENOME", "Credito pessoal", "1.000,00"],
        ]

        result = redactor.table(rows)

        assert result[0] == rows[0]
        assert result[1][0] == redact.SYNTHETIC_TEXT
        assert result[1][1] == "Credito pessoal"

    def test_non_personal_columns_keep_their_shape(self, redactor):
        rows = [
            ["Instituicao", "Vencimento", "Parcelas"],
            ["BANCO EXEMPLO S.A.", "01/03/2028", "48"],
        ]

        result = redactor.table(rows)

        assert result[1] == ["BANCO EXEMPLO S.A.", "01/03/2028", "48"]

    def test_pattern_rules_still_run_on_ordinary_cells(self, redactor):
        rows = [["Instituicao", "CNPJ"], ["BANCO X", "45.997.418/0001-53"]]

        result = redactor.table(rows)

        assert result[1][1] == "00.000.000/0000-00"

    def test_an_empty_table_is_handled(self, redactor):
        assert redactor.table([]) == []

    def test_a_header_only_table_is_handled(self, redactor):
        rows = [["Titular", "Saldo"]]

        assert redactor.table(rows) == rows


class TestTableHeaderRowIsNotTrusted:
    """The regression that leaked a real name and CPF 31 times.

    An earlier version copied a table's first row verbatim, on the assumption
    that it holds column labels. In a real SCR report, PDF extraction put the
    PAGE header into that row: name and CPF, repeated on every page, passing
    through untouched while the tool reported success on everything else.

    The shape below is the one that broke, with synthetic values.
    """

    PAGE_HEADER = (
        "Relatório de Empréstimos e Financiamentos (SCR)\n"
        "Página 1 de 31\n"
        "Nome: ALGUEM SOBRENOME\n"
        "CPF/CNPJ: 529.982.247-25"
    )

    def test_a_page_header_in_the_first_row_is_redacted(self, redactor):
        result = redactor.table([[self.PAGE_HEADER], ["some data"]])

        header = result[0][0]
        assert "ALGUEM SOBRENOME" not in header
        assert "529.982.247-25" not in header

    def test_the_structural_parts_of_that_header_survive(self, redactor):
        # A parser uses these to find page boundaries and the report type, so
        # redacting the whole cell would have destroyed the format.
        header = redactor.table([[self.PAGE_HEADER], ["x"]])[0][0]

        assert "Relatório de Empréstimos e Financiamentos (SCR)" in header
        assert "Página 1 de 31" in header

    def test_ordinary_column_labels_are_untouched(self, redactor):
        rows = [["Instituicao", "CNPJ", "Saldo devedor"], ["BANCO X", "1", "2"]]

        assert redactor.table(rows)[0] == rows[0]

    def test_column_detection_still_works_after_the_header_is_redacted(self, redactor):
        # Personal columns are identified from the header BEFORE it is
        # rewritten; getting that order wrong would stop the detection
        # working at all.
        rows = [
            ["Titular dos dados", "Modalidade"],
            ["ALGUEM SOBRENOME", "Credito pessoal"],
        ]

        result = redactor.table(rows)

        assert result[0][0] == "Titular dos dados"
        assert "ALGUEM" not in result[1][0]
        assert result[1][1] == "Credito pessoal"

    def test_a_cpf_anywhere_in_a_header_cell_is_caught(self, redactor):
        result = redactor.table([["Doc do titular 529.982.247-25"], ["x"]])

        assert "529.982.247-25" not in result[0][0]
