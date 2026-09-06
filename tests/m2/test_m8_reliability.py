"""M8 API failure-safety and database reliability regression tests."""

from __future__ import annotations

import logging

from sqlalchemy.exc import OperationalError


def test_m8_database_failure_returns_a_safe_service_error(client, monkeypatch, caplog) -> None:
    def unavailable(_session):
        raise OperationalError("select 1", {}, RuntimeError("connection refused"))

    monkeypatch.setattr("api.app.main.production_workforce_overview", unavailable)
    with caplog.at_level(logging.ERROR, logger="api.app.main"):
        response = client.get("/api/workforce/overview")

    assert response.status_code == 503
    assert response.json() == {"detail": "The workforce data service is temporarily unavailable."}
    assert "connection refused" not in response.text
    assert "Database request failed" in caplog.text


def test_m8_malformed_api_payload_returns_validation_without_a_solver_result(client) -> None:
    response = client.post("/api/workforce/scenario/optimize", content="not-json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert "recommendations" not in response.text
