# CreditRadar — agent instructions

Personal credit intelligence and readiness system for the Brazilian credit
market. Tracked in Jira as **V1C-76**, which is the primary product
specification for this repository.

## What this system is

It consolidates credit information fragmented across bureaus (Serasa, Quod,
SPC, Equifax/BoaVista), Banco Central (SCR/Registrato and public datasets),
banks and creditors, into a historical, explainable view of one person's
credit position. It is not a debt tracker: it exists to support decisions
about settling debts, repairing credit and judging whether a financing offer
is worth taking.

## Non-negotiable safety invariant

CreditRadar **never** performs a financial action. It does not accept
settlement agreements, generate payments, authorize transactions, request
loans, apply for financing or open financial products. It observes,
normalizes and explains; anything that creates a financial obligation is
performed by the user, outside this system.

Any internal readiness or scoring indicator is a **CreditRadar heuristic**
and must be labelled as such. Never present one as a prediction of a bank's
or bureau's proprietary approval model.

## Architecture

```text
Browser → Next.js → FastAPI → services → domain → persistence
                                      └→ providers → BCB, bureaus, SCR
```

```text
credit-radar/
├── backend/    FastAPI, Python 3.13, uv, SQLAlchemy, Alembic
├── frontend/   Next.js, React, TypeScript, pnpm, shadcn/ui, Recharts
├── docs/
├── flake.nix   Nix devShell: interpreters and system tooling
└── docker-compose.yml
```

The frontend never talks to a provider, a browser-automation worker or the
database. All financial data flows through the backend.

Dependency boundary, kept explicit:

| Tool   | Owns                                   |
| ------ | -------------------------------------- |
| Nix    | development environment, system deps   |
| uv     | Python dependencies                    |
| pnpm   | frontend dependencies                  |
| Docker | running services                       |

Do not introduce Poetry, pipenv, npm, Yarn or Bun.

## Data modelling rules

- **History is the product.** Model as `Entity + Observation + Source +
  ObservedAt`. Never overwrite the previous state.
- **Provenance is mandatory.** Every collected value records its source,
  upstream reference, collector version and collection time. Every
  collection attempt is recorded, including failures — a gap is only
  explainable if the attempt was logged, and runs cannot be backfilled.
- **`reference_date` ≠ `collected_at`.** A reference date may be in the
  future: the Copom publishes the Selic target ahead of the dates it applies
  to.
- **`Decimal`, never `float`,** for any monetary or rate value. The API
  serializes them as JSON strings, because a JSON number is an IEEE-754
  double in the browser.
- **Preserve the source's scale.** "14.00" is not "14"; the trailing zero
  states the precision published. The database column is unconstrained
  `numeric` for this reason.
- **Keep bureaus separate.** Serasa, Quod, SPC and Equifax use different
  methodologies. Never merge them into a synthetic universal score.
- Preserve these distinctions: `Debt ≠ NegativeRecord ≠ SettlementOffer`;
  `CreditScore ≠ Creditworthiness ≠ Affordability`; `CreditAvailability ≠
  CreditAttractiveness`; "Can I get credit?" ≠ "Should I take it?".

## Provider rules

Integrate in this order of preference: official API → structured export →
downloadable report → authenticated browser automation → DOM scraping.
Check for a stable structured integration before writing automation.

**Verify a source's identity before trusting it.** Series codes and endpoint
meanings are checked against the provider's own catalog, never inferred from
a plausible-looking value. This caught a mortgage series that was labelled
market-rate but was in fact the regulated-rate series — a 3+ percentage
point error in exactly the comparison the product exists to make.

Never bypass CAPTCHA, MFA, gov.br authentication or device confirmation.
Support human-assisted authentication instead. Treat session tokens and
browser profiles as secrets.

## Security

- Never commit credentials, CPF, financial records, session cookies, tokens,
  browser profiles or real credit reports.
- Never log secrets or personal data; redact sensitive fields.
- Nothing sensitive in `NEXT_PUBLIC_*` — those are inlined into the browser
  bundle. Provider credentials belong to the backend only.
- Services bind to loopback by default.
- Tests use synthetic or public fixtures. Never real credentials or real
  personal financial data.

## UI rules

- Never invent a value. Distinguish *loading*, *collected nothing* and
  *provider not implemented* as separate visible states.
- Show provenance: source, series, reference date, collection time.
- Show staleness and failed collections. Never present a stale or failed
  source as current.
- Application text is en-US. Numbers and rate notation follow Brazilian
  convention (`14,00% a.a.`), because that is how the source publishes them.

## Working rules

- **Everything in en-US**: code, comments, docs, commit messages, technical
  names, Jira technical comments.
- **Commit incrementally**, one coherent unit per commit. Never a single
  large commit at the end.
- **Never** add `Co-authored-by:` or attribute commits to Claude, Anthropic,
  an AI or any assistant.
- Before each commit: review the diff, check no secret was introduced, run
  the relevant checks.
- Keep the repository building and running as you advance.
- Sync meaningful decisions, discovered provider limitations, blockers and
  milestones to Jira V1C-76. Do not post trivial updates.

## Commands

```bash
nix develop                  # dev shell: python, uv, node, pnpm, psql

docker compose up -d         # full stack
docker compose up -d postgres

cd backend  && uv run ruff format . && uv run ruff check . \
            && uv run mypy && uv run pytest
cd frontend && pnpm lint && pnpm exec tsc --noEmit && pnpm build
```

Default host ports are offset (postgres 5434, backend 8007, frontend 3007)
because the development machine runs other projects on the conventional
ones. All are environment-overridable.
