"""Database engine, session, and schema setup (SQLAlchemy 2.0 + Postgres)."""
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to backend/.env (see backend/.env.example)."
        )
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables if they don't exist. Import models first so they register."""
    from core import models  # noqa: F401  (registers mappers on Base)

    Base.metadata.create_all(bind=get_engine())
    logger.info("Database schema ready")


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
