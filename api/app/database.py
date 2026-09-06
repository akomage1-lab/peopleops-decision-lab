"""PostgreSQL connection and session dependency for the M2 API."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DEFAULT_DATABASE_URL = "postgresql+psycopg:///peopleops_decision_lab"


def normalize_database_url(url: str) -> str:
    """Accept a standard hosted-PostgreSQL URL with the installed psycopg driver."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base for the intentionally small M2 schema."""


def get_session() -> Generator[Session, None, None]:
    """Yield one database session per API request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
