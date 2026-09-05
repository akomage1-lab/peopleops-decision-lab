"""PostgreSQL-backed fixtures for focused M2 integration tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.app.database import get_session
from api.app.main import create_app
from api.seed import seed_database


TEST_DATABASE_URL = os.getenv(
    "M2_TEST_DATABASE_URL",
    "postgresql+psycopg://wilmar@localhost:5432/peopleops_decision_lab_test",
)
ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "api" / "alembic"))
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_seeded_database() -> Generator[None, None, None]:
    """Prove downgrade/upgrade works, then seed a deterministic test database."""
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    config = _alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    test_engine = create_engine(TEST_DATABASE_URL)
    session_factory = sessionmaker(bind=test_engine)
    with session_factory() as session:
        seed_database(session)
    yield
    if original_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original_url


@pytest.fixture()
def session_factory():
    return sessionmaker(bind=create_engine(TEST_DATABASE_URL))


@pytest.fixture()
def client(session_factory) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
