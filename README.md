# CreditRadar

Personal credit intelligence and readiness system for the Brazilian credit
market.

CreditRadar consolidates credit information that is fragmented across bureaus
(Serasa, Quod, SPC, Equifax/BoaVista), Banco Central do Brasil (SCR/Registrato
and public market datasets), banks and creditors, in order to build a
**historical and explainable** view of one person's credit position.

It is not a debt tracker. It exists to answer decision questions:

- What debts exist under the CPF, and where can each be settled for the lowest total cost?
- Are there active negative records?
- How are the different bureau scores evolving, and what correlates with the changes?
- What credit exposure currently exists?
- Am I ready to finance a vehicle or a property?
- Is a given financing offer competitive against current market conditions?
- Should I take credit now, or wait for better personal or macroeconomic conditions?

Tracked in Jira as [V1C-76](https://v1cferr.atlassian.net/browse/V1C-76),
which is the primary product specification for this repository.

## Safety invariant

CreditRadar **never** performs a financial action on its own. It does not
accept settlement agreements, generate payments, authorize transactions,
request loans, apply for financing or open financial products. It observes,
normalizes and explains; every operation that creates a financial obligation
requires the user to act outside this system.

Its internal readiness indicators are **heuristics owned by this project**.
They are not predictions of any bank's or bureau's proprietary approval model.

## Status

The first end-to-end vertical slice is working:

```text
Banco Central SGS API → BCB provider → domain model → PostgreSQL
                     → FastAPI → Next.js → market dashboard and chart
```

| Area | State |
| --- | --- |
| Market indicators (Selic, IPCA, IGP-M, vehicle and mortgage rates) | Collected, stored with history and provenance, charted |
| Provider health and data-source auditing | Working |
| Credit scores per bureau | Not implemented — needs authenticated bureau providers |
| Debts, negative records, settlement offers | Not implemented |
| Credit exposure (SCR / Registrato) | Not implemented — needs gov.br authentication |
| Financing simulation (SAC, Price, CET) | Not implemented |
| Credit readiness indicators | Not implemented |

Unimplemented sections appear in the UI marked as such. Nothing displays an
invented figure.

## Architecture

```text
CreditRadar
├── Frontend — Next.js / React / TypeScript / shadcn/ui / Recharts
├── Backend  — FastAPI / Python 3.13 / SQLAlchemy / Alembic
├── Database — PostgreSQL
└── Infra    — Docker (services) / Nix (development environment)
```

```text
Browser
   │
   ▼
Next.js ── server-side fetch ──▶ FastAPI
                                   ├── services   (use cases)
                                   ├── domain     (entities, invariants)
                                   ├── persistence(append-only history)
                                   └── providers  ──▶ BCB SGS
                                                      bureaus (planned)
                                                      SCR / Registrato (planned)
```

The frontend never contacts Banco Central, a credit bureau, a browser
automation worker or the database. All financial data flows through the
backend, so every value the UI shows has passed through the domain layer and
carries its provenance.

Each tool owns one thing, deliberately:

| Tool | Owns |
| --- | --- |
| Nix | development environment and system dependencies |
| uv | Python dependencies |
| pnpm | frontend dependencies |
| Docker | running services |

### Design decisions worth knowing

- **History is the product.** Data is modelled as `Entity + Observation +
  Source + ObservedAt`. Nothing overwrites previous state. Re-collecting an
  unchanged value is a no-op; a changed value for an already-recorded date is
  stored as a revision, because upstream series such as IPCA get revised.
- **Provenance everywhere.** Every observation records its source, the
  upstream series identifier, the parser version and when it was collected.
  Every collection attempt is recorded even when it fails, so gaps in the
  history are explainable.
- **`Decimal`, never `float`.** Financial values are parsed from the
  published string, stored in unconstrained PostgreSQL `numeric` to preserve
  the published scale, and serialized to the frontend as JSON strings — a
  JSON number would arrive in the browser as an IEEE-754 double.
- **Bureaus stay separate.** Different bureaus use different methodologies;
  they are never merged into a synthetic universal score.

More detail in [`docs/`](docs/): [architecture](docs/architecture.md),
[domain model](docs/domain-model.md), [security](docs/security.md),
[authenticated providers](docs/authenticated-providers.md),
[BCB SGS provider](docs/providers/bcb-sgs.md).

## Getting started

### With Docker (whole stack)

```bash
cp .env.example .env          # adjust if the default ports collide
docker compose up -d
```

- Frontend — http://localhost:3007
- Backend — http://localhost:8007 (interactive docs at `/api/v1/docs`)
- PostgreSQL — `127.0.0.1:5434`

Ports default to an offset range because the development machine runs other
projects on 5432, 8000 and 3000. Override them in `.env`.

### For development

```bash
nix develop                   # python, uv, node, pnpm, psql, docker tooling

docker compose up -d postgres

cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn credit_radar.api.app:app --reload --port 8007

cd frontend                   # in another shell
cp .env.example .env.local
pnpm install
pnpm dev --port 3007
```

### Collecting market data

```bash
cd backend

# Routine collection: every indicator, over a window sized by its
# publication frequency. This is what the scheduled timer runs.
uv run credit-radar collect --quiet

# One indicator, explicit window, for backfilling history
uv run credit-radar collect --indicator SELIC_TARGET --from 2020-01-01 --to 2026-12-31
```

The window is frequency-aware on purpose. Collecting on a schedule exists to
catch **revisions**, not only new points: a monthly series such as IPCA is
revised after publication, so each run re-reads roughly thirteen months of it
and about a month of the daily series. Re-reading costs one request and
stores nothing when a value is unchanged.

`--quiet` logs only changes and failures, so a daily run leaves no trace in
the journal on a day when nothing moved.

Collection is also reachable over HTTP, which is what the dashboard's own
requests use:

```bash
curl -X POST "http://localhost:8007/api/v1/market/indicators/SELIC_TARGET/ingest?from=2024-01-01&to=2026-12-31"
```

Available indicator codes come from `GET /api/v1/market/indicators`.

## Deployment

Served at **https://credit.v1cferr.dev**, reachable from the home network and
over WireGuard only. From the public internet the reverse proxy answers 403.

That reach is not a default, it is the security control. This application has
no login of its own and holds a CPF, the debts under it, bureau scores and SCR
exposure, so exposing it publicly would publish a credit report. The reasoning
is recorded in the NixOS configuration that owns the ingress:

- `hosts/nixos-kingston/services.nix` — the `credit` entry, `expose = "lan"`
- `system/services/credit-radar.nix` — the stack brought up at boot
- `docs/notes/services/credit-radar.md` — why LAN, and why basic auth would
  not have helped

The proxy sends `/api/*` and `/health` to the backend and everything else to
the frontend, which is why the backend keeps its whole surface (interactive
docs and OpenAPI schema included) under `/api/v1`. Browser-side requests are
same-origin, so the client bundle never learns the API's address and the app
uses no `NEXT_PUBLIC_*` variable at all.

Making it reachable from outside the house would need application
authentication first, not a change to `expose`.

## Checks

```bash
cd backend  && uv run ruff format . && uv run ruff check . \
            && uv run mypy && uv run pytest
cd frontend && pnpm lint && pnpm exec tsc --noEmit && pnpm build
```

Backend integration tests need PostgreSQL and skip cleanly without it.

## Security

This project will process highly sensitive financial and identity
information. See [`docs/security.md`](docs/security.md). In short:

- No credentials, CPF, financial records, session cookies, tokens, browser
  profiles or real credit reports are ever committed.
- Nothing sensitive goes in `NEXT_PUBLIC_*`: those values are inlined into
  the browser bundle. Provider credentials belong to the backend alone.
- Services bind to loopback by default; the database is never exposed to the
  network.
- Tests use public or synthetic fixtures, never real personal data.
- CAPTCHA, MFA and gov.br authentication are never bypassed; human-assisted
  authentication is supported instead.

## Roadmap

Phases follow V1C-76.

1. **Discovery and recovery** — collect scores, discover debts and negative
   records, ingest SCR exposure, compare settlement offers.
2. **Credit optimization** — track score evolution, monitor inquiries and
   exposure, generate explainable recommendations.
3. **Credit readiness** — SAC and Price simulations, CET, affordability,
   vehicle and home readiness indicators.
4. **Personal credit intelligence** — longitudinal analysis, correlate credit
   events with profile changes, scenario modelling.

Market data collection came first deliberately: it validated the provider
architecture, normalization, historical persistence, provenance, the API and
the UI without touching authentication or personal data.
