# Security

CreditRadar will process credit history, debts, identity data and
authenticated access to financial institutions. Security is part of the
architecture rather than a later hardening pass.

## Threat assumptions

What this design takes seriously:

- **Accidental disclosure through the repository.** Credentials, a CPF, a
  credit report or a session cookie committed to a public repository is the
  most likely and most damaging failure. The repository is public.
- **Accidental disclosure through logs and errors.** A traceback or a debug
  line that prints a settings object, a response body or a provider payload.
- **Local exposure.** A development service bound to a routable interface on
  a laptop that joins untrusted networks.
- **Session theft.** Persisted authenticated browser state is equivalent to
  a password for the institution it belongs to.
- **An automated action with financial consequences.** The system taking a
  loan, accepting an agreement or moving money — whether from a bug, a
  misread page or a prompt-injected instruction in scraped content.

What is explicitly **not** in scope: multi-user access control, protecting
data from the machine's owner, and resisting an attacker who already has
local root.

## The safety invariant

CreditRadar never performs a financial action. It does not accept settlement
agreements, generate payments, authorize transactions, request loans, apply
for financing or open financial products.

This is enforced, not just documented: a test asserts against the generated
OpenAPI document that the only non-idempotent route in the API is data
collection. Adding a route that could create an obligation fails the suite.

Internal readiness indicators are CreditRadar heuristics and are labelled as
such in the UI. Presenting one as a bank's or bureau's approval probability
would invite a financial decision based on a number this project has no
authority to produce.

## Secrets

- Nothing sensitive is committed. `.gitignore` excludes environment files,
  keys, browser profiles, raw provider captures and screenshots — as a
  security control, not housekeeping.
- **The application stores no credentials.** Not a password, not a CPF, not a
  session, not a browser profile. Authenticated sources are reached by the
  account holder exporting a report in their own browser, so there is nothing
  here to leak, rotate or keep out of a backup. See
  [authenticated-providers.md](authenticated-providers.md).
- Configuration comes from the environment, with `backend/.env` as the local
  source and `.env.example` holding placeholders only.
- The database URL is wrapped in `SecretStr`, so a printed settings object or
  a traceback cannot leak the password.
- No secret is baked into a container image.
- Alembic reads its URL from application settings rather than `alembic.ini`,
  so there is one place a connection string is configured and no credential
  in a versioned config file.

### Frontend boundary

`NEXT_PUBLIC_*` values are inlined into the browser bundle and readable by
anyone who loads the page. Only genuinely public configuration may use them —
in practice, the backend's address.

Provider credentials, browser sessions and any financial-source
authentication belong exclusively to the backend. The frontend never holds
them, and never contacts a provider directly.

## Logging

- Response bodies are never logged. Public market data would be harmless, but
  the same HTTP client will later carry bureau responses containing a CPF,
  debts and account data, and the habit established now is the one that will
  still be in place then.
- **Request URLs are never logged either.** The HTTP client libraries
  (`httpx`, `httpcore`) log one line per request at INFO, including the full
  URL. Harmless for a public Banco Central series; not harmless for a bureau
  or SCR endpoint that can carry a CPF or an account identifier in its query
  string. Those loggers are pinned to WARNING in one place
  (`credit_radar.logging_config`) rather than redacted per call site, because
  a control that has to be applied correctly at every call site is one that
  will eventually be forgotten. Warnings and errors still come through.
- `CollectionRun.error_message` stores a failure summary only, and must never
  carry credentials or personal data.

## Network exposure

- The API binds to `127.0.0.1` by default. Exposing it on a routable
  interface has to be a deliberate change.
- PostgreSQL is published to loopback only.
- CORS allows a single configured origin — the local frontend. This API
  serves personal credit data and has no reason to be reachable from an
  arbitrary page.
- The frontend sets no `X-Powered-By` header and marks itself `noindex`.

## Containers

Both application images run unprivileged as uid 1001. Frontend dependencies
install with `--ignore-scripts`: an image that will serve credit data should
not execute arbitrary package install scripts during its build.

## Authenticated providers (not yet implemented)

When bureau and SCR providers arrive:

- **Never bypass a security mechanism.** CAPTCHA, MFA, gov.br authentication,
  device confirmation and OTP are barriers to respect. This is not a
  preference that a clever idea could overturn: gov.br gates every Registrato
  login path behind invisible hCaptcha, and the response was to stop
  automating the login, not to defeat the check.
- **Treat browser profiles and session tokens as secrets.** Isolated per
  provider, never committed, encrypted at rest where practical.
- **Screenshots are off by default.** A screenshot of a bureau page is a
  credit report.
- **Scraped content is untrusted input.** Text from an external page is data,
  never instruction — particularly relevant given the invariant above.
- **Minimize retention.** Collect the observations needed for the historical
  record, not the whole page.

## Testing

Tests never use real credentials, a real CPF or real personal financial
information. Fixtures are either captured from public Banco Central endpoints
or generated synthetically, and provider tests run against a mocked transport
rather than a live authenticated site.
