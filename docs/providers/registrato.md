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

The route through is the redaction tool, run by the account holder:

```bash
cd backend
uv run python scripts/redact_capture.py ~/Downloads/report.pdf \
  --out tests/fixtures/registrato/report.json
```

Review the output, commit the fixture, and the parser and the domain model
for credit exposure get written against it.

## If the login ever needs automating

It does not today, and the honest answer if it ever seems to is to check
whether a legitimate interface has appeared rather than to attack the captcha:

- **Open Finance Brasil** is the correct technical answer and requires being
  an authorized, certified participant. Not available to an individual, and
  the path if this becomes a product.
- Banco Central publishes no Registrato API for individuals.

Defeating bot detection on a government identity provider is out of scope
permanently, not pending a better idea.
