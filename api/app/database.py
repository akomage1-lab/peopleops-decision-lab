"""PostgreSQL connection and session dependency for the M2 API."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DEFAULT_DATABASE_URL = "postgresql+psycopg:///peopleops_decision_lab"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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
