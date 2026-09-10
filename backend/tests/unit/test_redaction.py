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

    def test_a_pdf_is_refused(self, redact, tmp_path):
        # The dangerous case. A PDF keeps its text in compressed streams, so
        # these rules find nothing and would report "nothing matched" over a
        # document that still holds a CPF. A false clean bill of health on a
        # credit report is worse than no tool, because the output looks
        # reviewed.
        source = tmp_path / "report.pdf"
        source.write_bytes(b"%PDF-1.7\n binary junk \x00\x01")

        with pytest.raises(SystemExit):
            redact._reject_binary(source)

    def test_a_zip_or_xlsx_is_refused(self, redact, tmp_path):
        source = tmp_path / "report.xlsx"
        source.write_bytes(b"PK\x03\x04 rest")

        with pytest.raises(SystemExit):
            redact._reject_binary(source)

    def test_plain_text_passes(self, redact, tmp_path):
        source = tmp_path / "report.csv"
        source.write_text("cpf;valor\n529.982.247-25;1.000,00\n", encoding="utf-8")

        redact._reject_binary(source)  # must not raise

    def test_json_passes(self, redact, tmp_path):
        source = tmp_path / "report.json"
        source.write_text('{"cpf": "529.982.247-25"}', encoding="utf-8")

        redact._reject_binary(source)  # must not raise

    def test_every_refused_signature_is_documented(self, redact):
        # A signature with no label would produce a refusal that does not say
        # what the file was or what to do instead.
        for signature, label in redact.BINARY_SIGNATURES.items():
            assert isinstance(signature, bytes)
            assert label
