"""Turn a real report into a fixture that is safe to commit and to review.

A parser cannot be written without knowing the format, and the format is
only visible in a real report, which is a CPF, a name and a complete credit
history. That file must not be shared with an assistant, pasted into a
conversation, or committed.

This is the way through. It runs on YOUR machine, over YOUR file, and
replaces identifiers and amounts with synthetic ones while keeping the
STRUCTURE: the same fields, the same nesting, the same field order, the same
number of characters where that matters. The parser is then written and
tested against the result, exactly as the Banco Central SGS parsers are.

    uv run python scripts/redact_capture.py real.json --out fixture.json

Read the output before committing it. This tool is a first pass by a machine
over a document only you have seen, so it cannot be the last word on whether
the file is safe. It prints a summary of what it changed and refuses to
overwrite an existing file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn

# --- Patterns ---------------------------------------------------------------
# Ordered most specific first, so a formatted CPF is not partly eaten by the
# bare-digit rule.

CPF_FORMATTED = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CNPJ_FORMATTED = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
CPF_BARE = re.compile(r"\b\d{11}\b")
CNPJ_BARE = re.compile(r"\b\d{14}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
# A separator after the area code is REQUIRED. Without it this pattern
# matched an unformatted eleven-digit CPF, since a mobile number and a
# CPF are both eleven digits: the value was still redacted, but under the
# wrong label and at the wrong length, which breaks a fixed-width format.
# An unformatted run of eleven digits in a credit report is a CPF far more
# often than a phone, so it falls through to CPF_BARE.
# A negative lookbehind rather than \b, because \b fails before an opening
# parenthesis: a space followed by "(" is non-word to non-word, so there is
# no boundary there and "(16) 98765-4321" would not match.
PHONE = re.compile(r"(?<![\w\d])(?:\+55[\s-]?)?(?:\(\d{2}\)|\d{2})[\s-]\d{4,5}[-\s]?\d{4}\b")
MONEY = re.compile(r"(?<![\d,.])\d{1,3}(?:\.\d{3})+,\d{2}(?![\d])")

# Replacements are obviously synthetic AND the same length as what they
# replace, so a fixed-width or column-aligned format still parses.
SYNTHETIC = {
    "cpf_formatted": "000.000.000-00",
    "cnpj_formatted": "00.000.000/0000-00",
    "cpf_bare": "00000000000",
    "cnpj_bare": "00000000000000",
    "email": "synthetic@example.invalid",
    "phone": "(00) 00000-0000",
}

# Field names whose VALUE is personal regardless of its shape. A name cannot
# be matched by a pattern, so it is matched by where it sits.
PERSONAL_KEYS = frozenset(
    {
        "nome",
        "nomecompleto",
        "nome_completo",
        "name",
        "fullname",
        "full_name",
        "razaosocial",
        "razao_social",
        "titular",
        "cliente",
        "datanascimento",
        "data_nascimento",
        "birthdate",
        "birth_date",
        "nascimento",
        "endereco",
        "address",
        "logradouro",
        "cep",
        "email",
        "telefone",
        "phone",
        "celular",
    }
)

# Reads as redacted rather than as a person. A `nome` field can hold the
# account holder OR an institution, and telling them apart would mean
# guessing from position in the document. Over-redacting is the safe
# direction, but the replacement should not impersonate a name in a slot
# where an institution belongs: the reviewer can restore a value that was
# never personal, and cannot un-leak one that was.
SYNTHETIC_NAME = "NOME REDIGIDO"
SYNTHETIC_DATE = "1990-01-01"
SYNTHETIC_TEXT = "VALOR SINTETICO"


def _fail(message: str) -> NoReturn:
    print(f"redact_capture: {message}", file=sys.stderr)
    raise SystemExit(1)


class Redactor:
    """Replaces personal content, counting what it touched."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()

    def _sub(self, pattern: re.Pattern[str], replacement: str, label: str, text: str) -> str:
        text, hits = pattern.subn(replacement, text)
        if hits:
            self.counts[label] += hits
        return text

    def text(self, value: str) -> str:
        value = self._sub(CPF_FORMATTED, SYNTHETIC["cpf_formatted"], "cpf", value)
        value = self._sub(CNPJ_FORMATTED, SYNTHETIC["cnpj_formatted"], "cnpj", value)
        value = self._sub(EMAIL, SYNTHETIC["email"], "email", value)
        value = self._sub(PHONE, SYNTHETIC["phone"], "phone", value)
        value = self._sub(CNPJ_BARE, SYNTHETIC["cnpj_bare"], "cnpj", value)
        value = self._sub(CPF_BARE, SYNTHETIC["cpf_bare"], "cpf", value)
        # Amounts are replaced too. They are not identifiers, but a committed
        # fixture of someone's real balances is still their financial
        # position, and a parser only needs the shape.
        value = self._sub(MONEY, "1.234,56", "amount", value)
        return value

    def by_key(self, key: str, value: Any) -> Any:
        """Replace a value because of the field it sits in."""
        normalized = key.lower().replace(" ", "").replace("-", "")
        if normalized not in PERSONAL_KEYS:
            return None

        self.counts[f"field:{normalized}"] += 1
        if "nasc" in normalized or "birth" in normalized:
            return SYNTHETIC_DATE
        if normalized in {
            "nome",
            "name",
            "fullname",
            "full_name",
            "nomecompleto",
            "nome_completo",
            "titular",
            "cliente",
            "razaosocial",
            "razao_social",
        }:
            return SYNTHETIC_NAME
        if normalized == "email":
            return SYNTHETIC["email"]
        if normalized in {"telefone", "phone", "celular"}:
            return SYNTHETIC["phone"]
        return SYNTHETIC_TEXT

    def walk(self, node: Any) -> Any:
        if isinstance(node, dict):
            result: dict[str, Any] = {}
            for key, value in node.items():
                replaced = self.by_key(key, value)
                result[key] = replaced if replaced is not None else self.walk(value)
            return result
        if isinstance(node, list):
            return [self.walk(item) for item in node]
        if isinstance(node, str):
            return self.text(node)
        # Numbers are left alone: a bare number carries no identity, and
        # changing every one would destroy the structure a parser is being
        # written against.
        return node


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="redact_capture",
        description=(
            "Replace personal content in a captured report with synthetic "
            "values, keeping the structure, so the result can be committed "
            "as a parser fixture. Review the output before committing it."
        ),
    )
    parser.add_argument("source", type=Path, help="the real capture (JSON or text)")
    parser.add_argument("--out", type=Path, required=True, help="where to write the fixture")
    parser.add_argument("--force", action="store_true", help="overwrite the output if it exists")
    args = parser.parse_args()

    if not args.source.is_file():
        _fail(f"{args.source} is not a file")
    if args.out.exists() and not args.force:
        _fail(f"{args.out} exists; pass --force to overwrite")

    raw = args.source.read_text(encoding="utf-8")
    redactor = Redactor()

    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        # Not JSON: redact as text, which still covers a CSV or a plain
        # report dump.
        output = redactor.text(raw)
    else:
        output = json.dumps(redactor.walk(document), indent=2, ensure_ascii=False) + "\n"

    args.out.write_text(output, encoding="utf-8")

    print(f"redact_capture: wrote {args.out}")
    if redactor.counts:
        print("  replaced:")
        for label, count in sorted(redactor.counts.items()):
            print(f"    {label}: {count}")
    else:
        print("  replaced: nothing matched")
        print(
            "  That may mean the document holds no personal data, or that it "
            "holds it in a shape these rules do not recognise. Read the output "
            "before committing it."
        )

    if any(label.startswith("field:") for label in redactor.counts):
        print()
        print("  Some values were replaced because of the FIELD they sit in, which")
        print("  over-redacts by design: a `nome` can hold the account holder or an")
        print("  institution, and only you can tell which. Restoring a value that")
        print("  was never personal is safe; the reverse is not.")

    print()
    print("  REVIEW THE OUTPUT BEFORE COMMITTING. This is a first pass by a")
    print("  machine over a document only you have seen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
