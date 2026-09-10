"""FastAPI dependency wiring."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from credit_radar.config import Settings, get_settings
from credit_radar.persistence.database import get_session_factory
from credit_radar.providers.bcb.sgs import BcbSgsProvider
from credit_radar.providers.http import HttpClient
from credit_radar.services.market_ingestion import MarketIngestionService


def get_db_session() -> Iterator[Session]:
    """Yield a request-scoped session, committing if the request succeeded."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_sgs_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[BcbSgsProvider]:
    with HttpClient(timeout_seconds=settings.http_timeout_seconds) as http:
        yield BcbSgsProvider(http)


DbSession = Annotated[Session, Depends(get_db_session)]
SgsProvider = Annotated[BcbSgsProvider, Depends(get_sgs_provider)]


def get_market_ingestion_service(
    session: DbSession, provider: SgsProvider
) -> MarketIngestionService:
    return MarketIngestionService(provider, session)


IngestionService = Annotated[MarketIngestionService, Depends(get_market_ingestion_service)]
