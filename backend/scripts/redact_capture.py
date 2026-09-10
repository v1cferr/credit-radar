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
# The thousands separator is OPTIONAL. Requiring it meant every amount
# below a thousand passed through: a real report leaked 154 distinct
# sub-1000 values across 560 occurrences, which is a credit position in
# detail. Any Brazilian decimal with two places is money or a rate here,
# and both are the account holder's financial data.
MONEY = re.compile(r"(?<![\d,.])\d{1,3}(?:\.\d{3})*,\d{2}(?![\d])")

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
# Labels that introduce a personal value in FREE TEXT, as a PDF renders it.
# The field-name rules only fire on a JSON key, and extracted PDF text has no
# keys: "Titular: Fulano De Teste" is one string. Without this, a name and a
# birth date pass straight through while the tool reports success, which is
# the most dangerous shape a redaction failure can take.
LABELLED_PERSONAL = re.compile(
    r"(?im)^([ \t]*(?:nome(?:\s+completo)?|titular(?:\s+dos\s+dados)?|cliente|"
    r"raz[aã]o\s+social|data\s+de\s+nascimento|nascimento|endere[cç]o|"
    r"logradouro|cep|e-?mail|telefone|celular)"
    r"[ \t]*[:\-][ \t]*)(.+)$"
)

# A date cannot be matched by shape here: "Data base: 06/2026" and
# "Vencimento: 01/03/2028" are structure a parser needs, while a birth date is
# personal. Only the LABEL distinguishes them, which is why there is no
# general date rule.
# Institution names. In someone's own credit report these say WHO THEY OWE,
# which is private financial information and has no place in a committed
# fixture. A parser needs to know a string sits in that position, not which
# bank it names.
#
# Matched as a run of two or more ALL-CAPS words, which is how this report
# renders them, with the structural vocabulary allowlisted below. Column
# labels and prose are not upper-case, so they are unaffected.
# Every word must START with a letter and contain no digits. Allowing digits
# made this swallow "CPF 529.982.247-25" and "CNPJ 45.997.418/0001-53" whole,
# replacing an identifier with an institution placeholder: still redacted, but
# under the wrong label and destroying the field a parser reads.
INSTITUTION_RUN = re.compile(
    r"\b[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ&./'-]{1,}"
    r"(?:[ ,\-]+[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ&./'-]{1,}){1,8}\b"
)

UPPERCASE_ALLOWLIST = frozenset(
    {
        # This tool's own placeholders.
        "VALOR SINTETICO",
        "NOME REDIGIDO",
        # Structural vocabulary of the report.
        "SCR",
        "CPF",
        "CNPJ",
        "CPF/CNPJ",
        "NAO",
        "NÃO",
        "TOTAL",
        "R$",
    }
)

SYNTHETIC_INSTITUTION = "INSTITUICAO SINTETICA S.A."
SYNTHETIC_TOKEN = "XXXX"
SYNTHETIC_NAME = "NOME REDIGIDO"
SYNTHETIC_DATE = "1990-01-01"
SYNTHETIC_TEXT = "VALOR SINTETICO"


BINARY_SIGNATURES: dict[bytes, str] = {
    b"%PDF": "PDF",
    b"PK\x03\x04": "ZIP or XLSX",
    b"\xd0\xcf\x11\xe0": "legacy Office document",
}
"""Formats whose text these rules CANNOT see, and must not pretend to.

A PDF keeps its text in compressed content streams, so a regex over the raw
bytes finds nothing and the tool would report "nothing matched" over a
document that still contains a CPF. A false clean bill of health on a credit
report is worse than no tool at all, because the output looks reviewed.

Refused loudly instead. Extracting text first is the fix, and it has to be a
deliberate step with its own review, not an accident of running this.
"""


MIN_EXTRACTED_CHARS = 200
"""Below this, extraction almost certainly failed.

A scanned or image-only PDF yields little or no text. Redacting nothing and
writing a near-empty fixture would look like success, so it is reported as
the failure it is.
"""


def _reject_binary(path: Path, *, pdf_allowed: bool) -> None:
    head = path.read_bytes()[:8]
    for signature, label in BINARY_SIGNATURES.items():
        if not head.startswith(signature):
            continue
        if label == "PDF" and pdf_allowed:
            return
        hint = (
            "pass --pdf to extract its text first"
            if label == "PDF"
            else "export the report as CSV, JSON or text if the source offers it"
        )
        _fail(
            f"{path} looks like a {label}. These rules only see plain text, "
            f"and a {label} keeps its text compressed, so this would report "
            f"'nothing matched' over a document that still holds a CPF. "
            f"Fix: {hint}."
        )


def extract_pdf(path: Path) -> dict[str, Any]:
    """Extract a PDF's text and tables, keeping the structure a parser needs.

    Tables are pulled per page as rows of cells rather than flattened into a
    text blob, because the layout IS the format: a parser for a financial
    report needs to know which column held the balance, and reading that back
    out of reflowed prose is guesswork.

    Document metadata is deliberately NOT carried over. A PDF's author, title
    and subject routinely hold the name of the person it is about, and a
    fixture has no use for any of it.
    """
    try:
        import pdfplumber
    except ModuleNotFoundError as error:  # pragma: no cover
        _fail(f"reading a PDF needs pdfplumber: {error}")

    pages: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            tables = [
                [[cell if cell is not None else "" for cell in row] for row in table]
                for table in (page.extract_tables() or [])
            ]
            # Word positions, because the COLUMN an amount sits in is the
            # difference between a balance that is current and one that is
            # overdue, and flowing the page into text throws that away. The
            # geometry is structure, not content: it says which column, never
            # what value.
            words = [
                {
                    "text": word["text"],
                    "x0": round(float(word["x0"]), 1),
                    "x1": round(float(word["x1"]), 1),
                    "top": round(float(word["top"]), 1),
                }
                for word in (page.extract_words() or [])
            ]
            pages.append(
                {
                    "page": number,
                    "text": page.extract_text() or "",
                    "tables": tables,
                    "words": words,
                }
            )

    return {
        "source_format": "pdf",
        "page_count": len(pages),
        "pages": pages,
    }


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
        # Labelled values first: a name has no shape of its own, so the label
        # is the only thing that can find it.
        value, hits = LABELLED_PERSONAL.subn(lambda m: m.group(1) + SYNTHETIC_TEXT, value)
        if hits:
            self.counts["labelled personal value"] += hits

        value = self._sub(CPF_FORMATTED, SYNTHETIC["cpf_formatted"], "cpf", value)
        value = self._sub(CNPJ_FORMATTED, SYNTHETIC["cnpj_formatted"], "cnpj", value)
        value = self._sub(EMAIL, SYNTHETIC["email"], "email", value)
        value = self._sub(PHONE, SYNTHETIC["phone"], "phone", value)
        value = self._sub(CNPJ_BARE, SYNTHETIC["cnpj_bare"], "cnpj", value)
        value = self._sub(CPF_BARE, SYNTHETIC["cpf_bare"], "cpf", value)
        # Amounts are replaced too. They are not identifiers, but a committed
        # fixture of someone's real balances is still their financial
        # position, and a parser only needs the shape.
        value = self._redact_institutions(value)

        # A FIXED placeholder, deliberately not one that preserves the
        # original's length. Matching the digit count would keep column
        # alignment, and would also reveal the magnitude: a five-digit
        # replacement says "this balance is in the tens of thousands", which
        # is exactly the financial detail being removed.
        value = self._sub(MONEY, "1.234,56", "amount", value)
        return value

    def _redact_institutions(self, value: str) -> str:
        """Replace runs of upper-case words that name an institution."""

        def replace(match: re.Match[str]) -> str:
            text = match.group(0)
            if text.strip() in UPPERCASE_ALLOWLIST:
                return text
            if all(word in UPPERCASE_ALLOWLIST for word in text.split()):
                return text
            self.counts["institution name"] += 1
            return SYNTHETIC_INSTITUTION

        return INSTITUTION_RUN.sub(replace, value)

    def words(self, words: list[dict[str, Any]], redacted_text: str) -> list[dict[str, Any]]:
        """Redact positioned words against the already-redacted page text.

        An invariant rather than another pattern: a token survives here ONLY
        if it still appears in the redacted text.

        Every label-based and multi-word rule is blind to this list, because a
        single word has no label and no neighbours. Adding it reintroduced a
        name leak in a new shape: "VICTOR" and "FERREIRA" as separate
        entries, which a search for the joined name does not find. Deriving
        the list from the redacted text closes that by construction, so a
        token redaction removed cannot come back through the geometry.
        """
        allowed = {
            token.strip(".,;:()[]/").casefold()
            for token in re.split(r"\s+", redacted_text)
            if token.strip(".,;:()[]/")
        }

        result: list[dict[str, Any]] = []
        for word in words:
            # The pattern rules run FIRST, then the invariant. Filtering the
            # raw token instead turned every amount into an opaque marker,
            # because "34,97" is not in a text that now reads "1.234,56", and
            # that destroyed the one thing this list exists for: knowing a
            # NUMBER sits at this x position, and therefore which column it
            # belongs to.
            token = self.text(str(word.get("text", "")))
            key = token.strip(".,;:()[]/").casefold()
            if key and key not in allowed:
                self.counts["positioned word"] += 1
                token = SYNTHETIC_TOKEN
            result.append({**word, "text": token})
        return result

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

    def table(self, rows: list[list[str]]) -> list[list[str]]:
        """Redact a table by column, using its header row.

        A cell holding a name carries no label of its own: in
        `["VICTOR FERREIRA", "476.366.418-28", ...]` only the header above it
        says what it is. So a header cell naming a personal field marks that
        whole column, and every value under it is replaced.
        """
        if not rows:
            return rows

        # The header is inspected for column labels and THEN redacted like any
        # other text. An earlier version copied it verbatim, on the assumption
        # that a first row holds column names. In a real report it held the
        # page header: name and CPF, repeated on all 31 pages, passing through
        # untouched while the tool reported success.
        header = rows[0]
        personal_columns = {
            index
            for index, cell in enumerate(header)
            if str(cell).lower().replace(" ", "").replace("-", "").rstrip("s")
            in {k.rstrip("s") for k in PERSONAL_KEYS}
            or any(
                word in str(cell).lower()
                for word in ("titular", "nome", "nascimento", "endereço", "endereco")
            )
        }

        # Text-level rules only: replacing a header cell wholesale would
        # destroy the column labels a parser is written against.
        redacted = [[self.text(str(cell)) for cell in header]]
        for row in rows[1:]:
            new_row = []
            for index, cell in enumerate(row):
                if index in personal_columns and str(cell).strip():
                    self.counts["personal table column"] += 1
                    new_row.append(SYNTHETIC_TEXT)
                else:
                    new_row.append(self.text(str(cell)))
            redacted.append(new_row)
        return redacted

    def walk(self, node: Any) -> Any:
        if isinstance(node, dict):
            result: dict[str, Any] = {}
            for key, value in node.items():
                if key == "tables" and isinstance(value, list):
                    result[key] = [
                        self.table(t) if isinstance(t, list) else self.walk(t) for t in value
                    ]
                    continue
                if key == "words" and isinstance(value, list):
                    # Needs this page's REDACTED text, which the "text" key
                    # produced earlier in this same loop. Extraction emits
                    # "text" before "words", and the assertion below refuses
                    # to guess if that ever stops being true.
                    if "text" not in result:
                        _fail(
                            "internal: 'words' was reached before 'text', so the "
                            "redacted text needed to filter it is not available"
                        )
                    result[key] = self.words(value, str(result["text"]))
                    continue
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


# Shapes that must never appear in a fixture unless they are a placeholder.
LEAK_PATTERNS: dict[str, str] = {
    "CPF": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
    "CNPJ": r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
    "long digit run": r"\b\d{11,14}\b",
    "decimal amount": r"(?<![\d,.])\d{1,3}(?:\.\d{3})*,\d{2}(?![\d])",
    "email": r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b",
    "CEP": r"\b\d{5}-\d{3}\b",
}

KNOWN_PLACEHOLDERS = frozenset(
    {
        SYNTHETIC["cpf_formatted"],
        SYNTHETIC["cnpj_formatted"],
        SYNTHETIC["cpf_bare"],
        SYNTHETIC["cnpj_bare"],
        SYNTHETIC["email"],
        SYNTHETIC["phone"],
        SYNTHETIC_NAME,
        SYNTHETIC_TEXT,
        SYNTHETIC_INSTITUTION,
        SYNTHETIC_TOKEN,
        SYNTHETIC_DATE,
        "1.234,56",
    }
)


def verify(path: Path) -> int:
    """Scan a fixture for anything that should not have survived redaction.

    For a fixture redacted from a REAL document. It answers "did redaction
    work", which is only a question about a redacted file. Pointed at a
    synthetic fixture it reports every amount as a leak, because it cannot
    tell an invented value from a surviving one, and "fixing" that by making
    the amounts identical would destroy the only thing a synthetic fixture is
    better at: proving the parser assigns an amount to the right column.

    A command rather than a snippet to paste, because a snippet carries a
    path relative to whichever directory the reader happened to be in, and
    getting that wrong looks like the fixture is missing rather than like the
    instruction was wrong.

    Two halves, deliberately separated. The pattern scan DECIDES: an
    identifier shape that is not a placeholder fails. The token listing does
    NOT decide, it reports, because only the person whose report this is can
    tell whether an upper-case word is a surname or a bank's trading name.
    Auto-classifying it would be the kind of false assurance this tool exists
    to avoid.
    """
    if not path.is_file():
        _fail(f"{path} is not a file")

    raw = path.read_text(encoding="utf-8")
    print(f"verify: {path} ({len(raw)} bytes)")
    print()

    leaks = 0
    print("  identifier shapes (a non-placeholder match is a leak):")
    for label, pattern in LEAK_PATTERNS.items():
        found = set(re.findall(pattern, raw))
        real = found - KNOWN_PLACEHOLDERS
        if real:
            leaks += len(real)
            shapes = sorted({re.sub(r"\d", "n", value) for value in real})[:3]
            print(f"    {label:16} LEAK: {len(real)} distinct, shapes {shapes}")
        else:
            print(f"    {label:16} clean")

    tokens: set[str] = set()
    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        tokens = set(re.findall(r"\b[^\s]{3,}\b", raw))
    else:
        for page in document.get("pages", []):
            for word in page.get("words", []):
                tokens.add(str(word.get("text", "")))
        if not tokens:
            tokens = set(re.findall(r"\b[^\s]{3,}\b", json.dumps(document)))

    caps = sorted(
        token
        for token in tokens
        if len(token) >= 3
        and token == token.upper()
        and re.search(r"[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ]", token)
        and token not in KNOWN_PLACEHOLDERS
    )

    print()
    print(f"  upper-case tokens to READ, not to trust ({len(caps)}):")
    for token in caps:
        print(f"    {token}")
    print()
    print("    None of the above is judged by this tool. A label, a placeholder")
    print("    or Banco Central vocabulary is expected; a surname is not, and")
    print("    only you can tell the difference.")

    print()
    if leaks:
        print(f"verify: {leaks} LEAK(S). Do not commit this fixture.")
        return 1
    print("verify: no identifier shapes survived. Read the token list above,")
    print("        then decide whether to commit.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="redact_capture",
        description=(
            "Replace personal content in a captured report with synthetic "
            "values, keeping the structure, so the result can be committed "
            "as a parser fixture. Review the output before committing it."
        ),
    )
    parser.add_argument(
        "source", type=Path, help="the real capture (JSON, CSV, text, or PDF with --pdf)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "scan a fixture REDACTED FROM A REAL DOCUMENT, to check that "
            "redaction worked. Not for a synthetic fixture: distinct amounts "
            "are the point of one, and this would report them as leaks."
        ),
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help=(
            "extract text and tables from a PDF before redacting. An explicit "
            "opt-in, because extraction can miss text that redaction then never "
            "sees."
        ),
    )
    parser.add_argument(
        "--out", type=Path, help="where to write the fixture (not used with --verify)"
    )
    parser.add_argument("--force", action="store_true", help="overwrite the output if it exists")
    args = parser.parse_args()

    if args.verify:
        return verify(args.source)

    if not args.source.is_file():
        _fail(f"{args.source} is not a file")
    _reject_binary(args.source, pdf_allowed=args.pdf)
    if args.out is None:
        parser.error("--out is required unless --verify is given")
    if args.out.exists() and not args.force:
        _fail(f"{args.out} exists; pass --force to overwrite")

    redactor = Redactor()
    extraction: dict[str, Any] | None = None

    if args.pdf:
        extraction = extract_pdf(args.source)
        characters = sum(len(page["text"]) for page in extraction["pages"])
        tables = sum(len(page["tables"]) for page in extraction["pages"])
        print(
            f"redact_capture: extracted {extraction['page_count']} page(s), "
            f"{tables} table(s), {characters} characters"
        )
        if characters < MIN_EXTRACTED_CHARS:
            _fail(
                f"only {characters} characters came out, which means extraction "
                f"failed rather than that the document is empty. A scanned or "
                f"image-only PDF needs OCR, and a fixture built from this would "
                f"be silently useless."
            )
        output = json.dumps(redactor.walk(extraction), indent=2, ensure_ascii=False) + "\n"
    else:
        raw = args.source.read_text(encoding="utf-8")
        try:
            document = json.loads(raw)
        except json.JSONDecodeError:
            # Not JSON: redact as text, which still covers a CSV or a plain
            # report dump.
            output = redactor.text(raw)
        else:
            output = json.dumps(redactor.walk(document), indent=2, ensure_ascii=False) + "\n"

    args.out.parent.mkdir(parents=True, exist_ok=True)
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
