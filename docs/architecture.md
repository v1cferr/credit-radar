# Architecture

## Shape

A modular monolith with explicit internal boundaries, not a distributed
system. This is a single-user personal application; the boundaries exist so
providers, analyzers and interfaces can evolve independently, not so they can
be deployed separately.

```text
frontend/  Next.js app — the only thing a browser talks to
backend/   FastAPI app
  api/          HTTP boundary: routers and request/response schemas
  services/     use cases; orchestrate providers and persistence
  domain/       entities, value objects, invariants. Depends on nothing.
  persistence/  SQLAlchemy models and repositories
  providers/    adapters translating external payloads into domain objects
```

Dependencies point inwards. `api` and `services` may use `domain`; `domain`
imports neither. A provider's job is to make external data disappear as
external: no SGS field name, HTML structure or bureau-specific shape exists
outside the provider that produced it.

## Synchronous by choice

The backend is synchronous throughout: `httpx.Client`, synchronous
SQLAlchemy, synchronous FastAPI handlers. For a single-user system with no
concurrency pressure, this keeps tests, migrations and request handling
simple, and avoids the failure modes of mixing async I/O with a synchronous
ORM. If concurrency is ever needed it belongs at the ingestion-scheduling
level, not spread through every layer.

## History is the product

Data is modelled as:

```text
Entity + Observation + Source + ObservedAt
```

An entity (a `MarketIndicator`, later a `Debt` or a `CreditBureau`) is stable.
An observation is one measured value of it, at one reference date, from one
source, with provenance. Nothing overwrites previous state.

Two properties come from a single unique constraint spanning the observation's
identity *and its value*:

- Re-collecting an unchanged value is a no-op, so a scheduled collector can
  run as often as it likes.
- A *changed* value for a reference date already on record inserts a new row
  beside the old one — a revision. Upstream series such as IPCA are revised
  after publication, and overwriting would erase the fact that the number
  moved.

`history()` returns the current revision per reference date (`DISTINCT ON`),
because a chart should show what the series says now. `revisions()` exposes
the full trail behind it.

## Provenance and auditability

Every observation answers: where did this come from, when was it collected,
which provider produced it, what parser version, and did that collection
succeed.

Collection attempts are recorded in their own table whether or not they
produce data, and in the same transaction as the observations. A run that
was never recorded is lost information — runs cannot be backfilled — which
is why the table exists before there was anything to debug with it.

`CollectionStatus` separates three outcomes that are easy to conflate:

| Status | Meaning |
| --- | --- |
| `success` | the source answered and data was parsed |
| `no_data` | the source authoritatively holds nothing for the request |
| `failed` | unreachable, timed out, or the payload broke the contract |

`no_data` is a fact worth storing; `failed` is a gap to retry.

## Numeric precision

Financial values never touch `float`.

- Parsed as `Decimal` from the source's published string; a float arriving in
  a payload is rejected rather than silently narrowed.
- Stored in **unconstrained** PostgreSQL `numeric`. Declaring a scale would
  pad every value to it, so a rate published as `14.00` would read back as
  `14.00000000`. The published scale is information about precision.
- Serialized to the frontend as JSON **strings**. A JSON number is an
  IEEE-754 double by the time it reaches the browser, so `14.00` would arrive
  as `14`.
- Formatted for display from the string, so what the user reads is what the
  source published.

An observation is also rejected if its unit contradicts the indicator
catalog. A per-day rate labelled per-year is not a wrong number but a
plausible one, which is what makes it dangerous downstream.

## API

Versioned under `/api/v1`, resource-oriented, and generic over indicators
rather than naming Selic in a route:

```text
GET  /api/v1/market/indicators
GET  /api/v1/market/summary
GET  /api/v1/market/indicators/{code}/observations
GET  /api/v1/market/indicators/{code}/observations/latest
POST /api/v1/market/indicators/{code}/ingest
GET  /health
```

`/summary` exists to serve the dashboard in one request: each indicator with
its current value and the outcome of its last collection. An indicator with
nothing collected returns a null `latest`, so the UI can say "no observations
yet" rather than being handed a zero that would read as a real rate.

A test asserts against the generated OpenAPI document that the only
non-idempotent route is data collection. The safety invariant is easier to
guarantee by pinning the HTTP surface than by reviewing it.

Everything the backend serves lives under `/api/v1`, the interactive docs and
the schema included, plus `/health` for operations. Behind a reverse proxy the
frontend owns the domain root, so a backend path outside that prefix would
either be unreachable or collide with a future page.

## Frontend

Next.js App Router. Data is fetched in server components through
`src/lib/api`, which keeps the API address off the client. Charts are client
components because Recharts needs the DOM.

Anything that does run in the browser calls the same origin, and `/api` is
routed to the backend by the proxy in front (or, in development, by a rewrite
in `next.config.ts`). Dev and deployment therefore behave identically, and the
client bundle never learns where the API lives: the application uses no
`NEXT_PUBLIC_*` variable at all. CORS remains configured on the backend, not
for the frontend's benefit but because the API port is reachable on the LAN
and a page should not be able to read it cross-origin.

Backend failures are values, not exceptions: a provider being unreachable is
an expected state to render honestly, not a crashed page. Results carry a
`fetchedAt` timestamp so staleness is judged against the moment the data was
observed, and every card on a page uses the same reference instant.

Types are hand-written rather than generated from OpenAPI. With one resource
area, generation would add a build step and a regeneration ritual to save
about fifty lines. Once debts, scores, exposure and financing exist it starts
paying for itself, and the document is already served at
`/api/v1/openapi.json`.

## Interface language

The UI is pt-BR; everything else in the repository is en-US. That split is
the exception the language rule explicitly allows for user-facing
localization, and it is drawn at what reaches a screen: page copy, titles,
metadata and accessible labels are Portuguese, while code, comments, docs and
commit messages are not.

The backend's `name` and `description` for an indicator are en-US domain
documentation and are deliberately not rendered. What the user should see an
indicator called is a presentation concern and lives in
`frontend/src/lib/labels.ts`, keyed by the stable internal indicator code,
which is what that code exists for. The maps are typed as exhaustive
`Record`s over the domain enums, so adding an indicator, unit or frequency
fails to compile until it has a label rather than putting a raw enum value on
screen.

No i18n library: there is one locale, and a framework for it would be
machinery without a second case to justify it. A library earns its place the
day a second language does.

## Known limitations

- **Chart payload size.** The market page sends the full daily Selic series
  to the browser — around 990 points for a two-year window, contributing most
  of a ~400 KB page. The Selic target is a step function that changes only at
  Copom meetings, so nearly all of those points are redundant. Compressing
  runs of equal values would be lossless for step series but not for the
  monthly rate series, so it needs a real decision rather than a quick fix.
- **Collection depends on the host's schedule.** `credit-radar collect` is
  the scheduled entry point, driven by a systemd timer in the NixOS config
  rather than by anything in this repository, so a checkout on another
  machine collects only when asked.
- **Single user, no authentication.** Deliberate: the service binds to
  loopback and is private. Multi-tenancy, RBAC and account management are out
  of scope.
