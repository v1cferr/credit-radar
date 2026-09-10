"""FastAPI application.

The only boundary the frontend talks to. Nothing outside this process is
allowed to reach a provider, a browser automation worker or the database
directly, so every piece of financial data the UI shows has passed through
the domain and carries its provenance.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from credit_radar.api.dependencies import DbSession
from credit_radar.api.routers import market
from credit_radar.api.schemas import HealthResponse
from credit_radar.config import get_settings
from credit_radar.logging_config import configure_logging

API_PREFIX = "/api/v1"

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="CreditRadar API",
        version="0.1.0",
        # Everything the backend serves lives under one prefix, the interactive
        # docs and the schema included. Behind a reverse proxy the frontend owns
        # the domain root, so a backend path outside /api/v1 would either be
        # unreachable or collide with a future page.
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        summary="Personal credit intelligence for the Brazilian credit market",
        description=(
            "Private, single-user API. It exposes observed data and internal "
            "analytical indicators only. It never performs a financial "
            "operation: settling a debt, taking credit or authorizing a "
            "payment always requires the user to act outside this system."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    v1 = APIRouter(prefix=API_PREFIX)
    v1.include_router(market.router)
    app.include_router(v1)

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health(session: DbSession) -> HealthResponse:
        """Liveness plus database reachability.

        The database is reported separately so a deployment that is up but
        cannot reach its storage is not mistaken for a healthy one.
        """
        try:
            session.execute(text("SELECT 1"))
            database = "reachable"
        except Exception:
            logger.exception("Health check could not reach the database")
            database = "unreachable"
        return HealthResponse(status="ok", database=database)

    return app


app = create_app()
