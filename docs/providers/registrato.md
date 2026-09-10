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

## The report's format

Learned by extracting a real report. This is FORMAT knowledge, not data, and
writing it down is what lets the parser be tested against a fixture nobody
has to trust.

The SCR report is a per-month history: one block per reference month, from
the oldest requested month to the newest, at roughly one month per page.

Each page carries a header (title, `Página N de M`, `Nome:`, `CPF/CNPJ:`),
then the column band, then the month's blocks.

```text
Dívidas                                  Outros compromissos financeiros
Instituição
        Em dia    Vencida    Crédito a liberar   Coobrigações   Limites de crédito
Mês de referência: 03/2026   R$ ...     R$ ...                      R$ ...
<institution>
  <modality>                            R$ ...
```

**Amounts are positional, not ordered.** A month line can carry one, two or
three amounts, and which columns they belong to is decided by the x
coordinate, not by their order. Measured header and value positions:

| Column | Header x | Value x |
| --- | --- | --- |
| Em dia | 322.5 | ~326 |
| Vencida | 408.0 | ~432 |
| Crédito a liberar | 564.9 | — |
| Coobrigações | 620.0 | — |
| Limites de crédito | 783.0 | ~750 |

That is the whole reason the fixture carries word geometry. Flowing the page
into text puts three amounts on one line with no way to tell a balance that
is current from one that is overdue, and in a report about debt that is the
entire distinction.

Institution and modality names wrap across lines, so a parser cannot assume
one row is one line.

## Parser fixtures are synthetic

Not derived from a real report, even a redacted one. Two reasons, and the
second is the one that decided it.

**A redacted report is still a document shaped by one person's finances**:
how many institutions, how many months, how many operations. This repository
is public, and six separate leaks were found in one such file before it read
clean, which is reason enough not to bet on getting the seventh right.

**A synthetic fixture is a better test.** Redaction replaces every amount
with the same placeholder, so a fixture built from a real report cannot
verify that the parser assigns amounts to the right column: every value looks
identical. A hand-written fixture gives each column a distinct value, which
is the one thing the parser most needs to get right.

So `backend/tests/fixtures/registrato/` holds invented reports built from the
format above, and a fixture derived from a real document is git-ignored.

### Every way this leaked

Six, found one at a time, and **every one of them in a run that reported
success**. A count of replacements is not evidence of a clean fixture.

| Leak | Cause |
| --- | --- |
| CPF invisible in raw bytes | PDF text is Flate-compressed, so regexes over bytes found nothing |
| Name and birth date in free text | Field rules fire on a JSON key, and extracted text has none: `Titular: X` is one string |
| Name and CPF, 31 times | A table's first row was copied verbatim; extraction had put the PAGE header there |
| 154 amounts, 560 occurrences | The money pattern required a thousands separator, so everything under R$ 1.000 passed |
| Institution names | Treated as non-personal until a real report made the point |
| Name split into `VICTOR` / `FERREIRA` | The positioned-words list has no labels and no neighbours, and a search for the joined name misses it |

Institution names deserve the explanation. In someone's own credit report
they say **who they owe**, which is private financial information with no
place in a committed fixture. A parser needs a string in that position, not
the name of a bank. What survives is Banco Central's own taxonomy
(`Cartão de crédito`, `Crédito pessoal - sem consignação em folha de
pagamento`), which a parser maps and which names nobody.

The last one was self-inflicted and is the most instructive: adding word
geometry reintroduced a leak that had already been fixed, in a shape the
existing check could not see. It is closed by an **invariant rather than
another pattern**: a token survives only if it appears in the
already-redacted text, so whatever redaction removed cannot return through
the geometry. The pattern rules run on each token *before* that check,
because filtering the raw token turned every amount into an opaque marker and
destroyed the one thing the list exists for.

Two smaller decisions worth keeping:

**The amount placeholder does not preserve length.** Matching the digit count
would keep column alignment and would reveal the magnitude, which is the
detail being removed.

**There is no general date rule.** `Data base: 06/2026` and
`Vencimento: 01/03/2028` are the format a parser is written against, while a
birth date is personal, and only the label separates them.

### Verifying a fixture before committing it

Not optional, and not by eye over half a megabyte of JSON:

```bash
cd backend
uv run python scripts/redact_capture.py --verify tests/fixtures/registrato/scr.json
```

A command rather than a snippet to paste, because a snippet carries a path
relative to whichever directory the reader happened to be in, and getting
that wrong looks like the fixture is missing rather than like the instruction
was wrong.

It has two halves, deliberately separated:

**The pattern scan decides.** A CPF, CNPJ, e-mail, CEP, long digit run or
decimal amount that is not a known placeholder fails the check, and the
command exits non-zero.

**The token listing does not decide, it reports.** Every upper-case word that
is not a placeholder is printed for you to read, because only the person
whose report this is can tell whether an upper-case word is a surname or a
bank's trading name. Auto-classifying that would be the false assurance this
tool exists to avoid. Month and year pairs are excluded: a token with no
letters cannot be a name, and would only bury the ones that matter.

The downloaded file's own name contains the CPF, so the fixture must not
inherit it, and the PDF is worth deleting once the fixture exists, since
`~/Downloads` is inside the backup.


## If the login ever needs automating

It does not today, and the honest answer if it ever seems to is to check
whether a legitimate interface has appeared rather than to attack the captcha:

- **Open Finance Brasil** is the correct technical answer and requires being
  an authorized, certified participant. Not available to an individual, and
  the path if this becomes a product.
- Banco Central publishes no Registrato API for individuals.

Defeating bot detection on a government identity provider is out of scope
permanently, not pending a better idea.
