# Banco Central Registrato, and why its login is not automated

Registrato holds the credit exposure Banco Central records under a CPF: loans,
financing contracts, limits, outstanding and overdue balances. It is the
single most valuable authenticated source for this project.

Its login **cannot be automated, and this project will not try.**

## What was measured

`sso.acesso.gov.br` protects the sign-in with **invisible hCaptcha**:

```html
<div id="hcaptcha"></div>
hcaptcha.render('hcaptcha', {
  sitekey: "93b08d40-...", size: "invisible", callback: onHcaptchaCallback
})

function onSubmit(event) { ... hcaptcha.execute(window.hcaptchaWidgetId); }
function onHcaptchaCallback(token) { document.getElementById('loginData').submit(); }
```

The form is never posted without a captcha token, and **every** sign-in path
routes through that same handler:

| Path | Route to the gate |
| --- | --- |
| CPF and password | `enter-account-id` → `onSubmit` |
| Login with a bank | `login-external-authentication` → `onSubmit` |
| QR code, gov.br app | `pollVerifyQrCode` → `hcaptcha.execute` |
| Digital certificate | `login-certificate` → `onSubmit` |
| Cloud certificate | `login-external-authentication` → `onSubmit` |

So there is no alternative credential that avoids it. A digital certificate
looked like it might, and does not.

A Playwright-driven Chromium is scored as automated, the token is refused and
the POST returns `400` with `Captcha inválido. Tente novamente.
(ERL0000900)`. That is the mechanism working correctly, not a bug to route
around.

The page itself renders fine under automation, incidentally: eight inputs,
thirty-two buttons, 37 KB of markup, with `navigator.webdriver` true. Nothing
blocks *reading* the login page. What is protected is *submitting* it.

## The consequence: the human exports, the application ingests

This is not a workaround, it is a better fit for the acquisition strategy this
project already had. A downloadable report is tier three; browser automation
is tier five. The report was always the preferable integration and the
automation was the detour.

```text
you, in your ordinary browser  ->  Registrato  ->  download the report
                                                      |
                                                      v
                                   credit-radar imports the file
```

What that buys, beyond working at all:

- **The application holds no credentials.** No CPF, no password, no session,
  nothing to leak, rotate or keep out of a backup. The credential layer and
  the browser layer were both removed because nothing needs them.
- **No session expiry.** gov.br sessions are short, so an automated collector
  would have needed a person to re-authenticate every few hours anyway. The
  cadence was always going to be "when you log in".
- **No fight with a security control**, and nothing that could be read as
  circumventing one.

## What is still missing

The parser. A parser needs the report's format, and the format is only
visible in a real report, which is a CPF plus a full credit history and must
not be shared or committed.

The report downloads as a **PDF**, which needed two fixes to the redaction
tool before it could produce a fixture safely.

```bash
cd backend
uv run python scripts/redact_capture.py --pdf \
  ~/Downloads/<the SCR pdf> \
  --out tests/fixtures/registrato/scr.json
```

`--pdf` is an explicit opt-in, because extraction can miss text that
redaction then never sees. The tool reports how many pages, tables and
characters came out, and refuses outright when too little text appears, since
a scanned PDF would otherwise produce a silently useless fixture.

Extraction keeps tables as rows of cells rather than flattening them into
prose. For a financial report the layout IS the format: a parser needs to
know which column held the balance, and recovering that from reflowed text is
guesswork.

### Three ways this leaked, one of them in a real report

The third was caught only by scanning the fixture generated from the real
document, which is why that scan is a required step and not a formality.

**A table's first row is not always column labels.** PDF extraction put the
page header into it, so `Nome: ...` and `CPF/CNPJ: ...` sat in row zero of a
table on all 31 pages. The tool copied header rows verbatim, on the
assumption that they hold column names, and reported success on everything
else: 192 amounts, 62 CPFs and 132 personal columns replaced, while the real
name and CPF passed through 31 times each.

Header cells are now redacted with the text-level rules, after being read for
column labels and before being rewritten. Only text rules apply, because
replacing a header cell wholesale would destroy the labels a parser needs.

### Two more ways this nearly leaked

Both were found by testing against a realistic synthetic PDF, and both would
have produced a fixture that looked reviewed.

**A PDF's text is compressed.** The original tool ran regexes over raw bytes,
so it found nothing in a real PDF and reported "replaced: nothing matched"
over a document that still held a CPF. Verified: in a Flate-compressed PDF
the CPF is not present in the raw bytes at all. Binary formats are now
refused unless extraction is explicitly requested.

**A name in free text has no key.** The field-name rules only fire on a JSON
key, and extracted PDF text has none: `Titular: Fulano De Teste` is a single
string. The name and the birth date passed straight through while the tool
reported success on the CPF and the amounts. Labelled values in text are now
redacted by their label, and table columns by their header, because a cell
holding a name carries no label of its own.

There is deliberately **no general date rule**: `Data base: 06/2026` and
`Vencimento: 01/03/2028` are the format a parser is written against, while a
birth date is personal, and only the label separates them.

### Five ways this leaked, found one at a time

Every one of them was in a run that reported success. **A count of
replacements is not evidence of a clean fixture.**

| Leak | Cause |
| --- | --- |
| CPF invisible in raw bytes | PDF text is Flate-compressed; regexes over bytes found nothing |
| Name and birth date in free text | Field rules fire on a JSON key, and extracted text has none: `Titular: X` is one string |
| Name and CPF, 31 times | A table's first row was copied verbatim; extraction had put the PAGE header there |
| 154 amounts, 560 occurrences | The money pattern required a thousands separator, so everything under R$ 1.000 passed |
| Name split into `VICTOR` / `FERREIRA` | The positioned-words list has no labels and no neighbours, and a search for the joined name misses it |

Institution names were also treated as non-personal until a real report made
the point: in someone's own credit report they say **who they owe**, which is
private financial information. They are now replaced too. What survives is
Banco Central's own taxonomy (`Cartão de crédito`, `Crédito pessoal - sem
consignação em folha de pagamento`), which a parser maps and which names
nobody.

The positioned-words list is protected by an **invariant rather than another
pattern**: a token survives only if it appears in the already-redacted text,
so whatever redaction removed cannot come back through the geometry.

The amount placeholder deliberately does **not** preserve the original's
length. Matching the digit count would keep column alignment and would reveal
the magnitude, which is the detail being removed.

### Verifying a fixture before committing it

Not optional, and not by eye over 100 KB of JSON. Scan it:

```bash
python - <<'EOF'
import re, pathlib
raw = pathlib.Path("tests/fixtures/registrato/scr.json").read_text()
placeholders = {"000.000.000-00", "00.000.000/0000-00", "00000000000"}
for label, pattern in {
    "CPF":   r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
    "CNPJ":  r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
    "11dig": r"\b\d{11}\b",
    "email": r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b",
    "CEP":   r"\b\d{5}-\d{3}\b",
}.items():
    real = {h for h in re.findall(pattern, raw)} - placeholders
    print(f"{label}: {'clean' if not real else f'{len(real)} LEAK(S)'}")
print("also grep for your own name and address by hand")
EOF
```

**Check the tokenized forms too.** A search for a joined name misses a name
split across the positioned-words list, which is how one leak survived a scan
that reported clean:

```bash
python -c "
import json
d = json.load(open('tests/fixtures/registrato/scr.json'))
caps = {w['text'] for p in d['pages'] for w in p['words']
        if len(w['text']) >= 3 and w['text'] == w['text'].upper()}
print(sorted(caps))"
```

Every token that comes back should be a label, a placeholder, or Banco
Central's vocabulary. A surname will stand out.

A count of replacements is not evidence of a clean fixture: the leak above
happened in a run that reported 386 successful replacements.

The downloaded file's own name contains the CPF, so the fixture must not
inherit it, and the PDF is worth deleting from `~/Downloads` once the fixture
exists, since that directory is inside the backup.

## If the login ever needs automating

It does not today, and the honest answer if it ever seems to is to check
whether a legitimate interface has appeared rather than to attack the captcha:

- **Open Finance Brasil** is the correct technical answer and requires being
  an authorized, certified participant. Not available to an individual, and
  the path if this becomes a product.
- Banco Central publishes no Registrato API for individuals.

Defeating bot detection on a government identity provider is out of scope
permanently, not pending a better idea.
