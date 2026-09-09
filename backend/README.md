# CreditRadar backend

FastAPI application and domain core. See the repository root README for the
full-stack overview and development workflow.

## Layout

```text
src/credit_radar/
  config.py       environment-based settings
  domain/         entities, value objects and invariants
  providers/      external source adapters (BCB SGS today)
  persistence/    SQLAlchemy models and repositories
  services/       application services / use cases
  api/            FastAPI routers and request/response schemas
```

Dependencies flow inwards: `api` and `services` may depend on `domain`,
never the reverse. `providers` translate external payloads into domain
objects, so no source-specific field name leaks past that boundary.

## Commands

```bash
uv sync                 # install dependencies
uv run ruff format .    # format
uv run ruff check .     # lint
uv run mypy             # type check (strict)
uv run pytest           # tests
```

Tests never contact an external service or use real personal data. Provider
payloads are captured from public Banco Central endpoints or generated
synthetically.
