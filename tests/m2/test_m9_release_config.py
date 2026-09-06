"""M9.1 deployment configuration and public-release safety checks."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from api.app.database import normalize_database_url
from api.app.main import LOCAL_FRONTEND_ORIGINS, cors_origins_from_environment, create_app


ROOT = Path(__file__).resolve().parents[2]


def test_m9_normalizes_standard_hosted_postgresql_urls() -> None:
    hosted_url = "postgresql://user:password@ep-example.us-east-2.aws.neon.tech/app?sslmode=require"

    assert normalize_database_url(hosted_url) == (
        "postgresql+psycopg://user:password@ep-example.us-east-2.aws.neon.tech/app?sslmode=require"
    )
    assert normalize_database_url("postgres://user:password@host/app") == (
        "postgresql+psycopg://user:password@host/app"
    )
    assert normalize_database_url("postgresql+psycopg:///peopleops_decision_lab") == (
        "postgresql+psycopg:///peopleops_decision_lab"
    )


def test_m9_alembic_uses_psycopg_for_standard_hosted_postgresql_url(monkeypatch) -> None:
    hosted_url = "postgresql://user:password@ep-example.us-east-2.aws.neon.tech/app?sslmode=require"
    config = Config(str(ROOT / "alembic.ini"), output_buffer=io.StringIO())
    config.set_main_option("script_location", str(ROOT / "api" / "alembic"))
    monkeypatch.setenv("DATABASE_URL", hosted_url)

    command.upgrade(config, "head", sql=True)

    assert config.get_main_option("sqlalchemy.url") == normalize_database_url(hosted_url)


def test_m9_development_cors_defaults_to_explicit_local_origins(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    assert cors_origins_from_environment() == LOCAL_FRONTEND_ORIGINS


def test_m9_production_cors_requires_explicit_origin(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS is required"):
        create_app()


def test_m9_production_cors_allows_only_configured_origin_without_credentials(monkeypatch) -> None:
    allowed_origin = "https://peopleops-decision-lab.vercel.app"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", f"{allowed_origin}/")

    with TestClient(create_app()) as client:
        allowed = client.options(
            "/health",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        rejected = client.options(
            "/health",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == allowed_origin
    assert "access-control-allow-credentials" not in allowed.headers
    assert "access-control-allow-origin" not in rejected.headers
