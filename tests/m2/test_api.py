"""Focused API/database integration tests for the M2 walking skeleton."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from api.app.models import ScenarioRecord, ScenarioRoleRecord
from api.app.service import optimize_record, to_engine_scenario
from api.seed import seed_database
from peopleops.forecast import forecast_workforce
from peopleops.optimizer import optimize_hiring_plan


def test_health_endpoint(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_seeded_scenario_retrieval_reads_postgresql_data(client) -> None:
    response = client.get("/api/scenarios/1")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "M2 Seeded Workforce Plan"
    assert body["planning_horizon_months"] == 6
    assert body["planning_period_incremental_workforce_budget"] == 170_000.0
    assert body["recruiting_capacity"] == [2, 2, 2, 2, 2, 2]
    assert len(body["roles"]) == 3


def test_optimize_endpoint_returns_real_m1_result_and_respects_budget(client) -> None:
    response = client.post("/api/scenarios/1/optimize", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["baseline_understaffed_fte_months"] > body["optimized_understaffed_fte_months"]
    assert body["incremental_workforce_spend_used"] <= body["available_budget"]
    assert body["solver_status"]["primary"] == "OPTIMAL"
    assert body["solver_status"]["secondary"] == "OPTIMAL"
    assert body["recommendations"]


def test_budget_override_reaches_optimizer_without_persisting(client) -> None:
    response = client.post(
        "/api/scenarios/1/optimize",
        json={"planning_period_incremental_workforce_budget": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available_budget"] == 0
    assert body["incremental_workforce_spend_used"] == 0
    assert body["optimized_understaffed_fte_months"] == pytest.approx(
        body["baseline_understaffed_fte_months"]
    )
    assert body["recommendations"] == []
    assert client.get("/api/scenarios/1").json()["planning_period_incremental_workforce_budget"] == 170_000.0


def test_negative_budget_is_rejected(client) -> None:
    response = client.post(
        "/api/scenarios/1/optimize",
        json={"planning_period_incremental_workforce_budget": -1},
    )
    assert response.status_code == 422


def test_api_matches_direct_existing_engine_for_the_same_postgresql_inputs(client, session_factory) -> None:
    with session_factory() as session:
        record = session.scalar(
            select(ScenarioRecord)
            .options(selectinload(ScenarioRecord.roles))
            .where(ScenarioRecord.id == 1)
        )
        assert record is not None
        direct_scenario = to_engine_scenario(record, budget_override=100_000.0)
        direct_baseline = forecast_workforce(direct_scenario)
        direct_result = optimize_hiring_plan(direct_scenario)

    response = client.post(
        "/api/scenarios/1/optimize",
        json={"planning_period_incremental_workforce_budget": 100_000.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["baseline_understaffed_fte_months"] == pytest.approx(
        direct_baseline.total_understaffed_fte_months
    )
    assert body["optimized_understaffed_fte_months"] == pytest.approx(
        direct_result.total_understaffed_fte_months
    )
    assert body["incremental_workforce_spend_used"] == pytest.approx(direct_result.budget_used)


def test_seed_is_reproducible(session_factory) -> None:
    with session_factory() as session:
        seed_database(session)
        seed_database(session)
        scenario_count = session.scalar(select(func.count()).select_from(ScenarioRecord))
        role_count = session.scalar(select(func.count()).select_from(ScenarioRoleRecord))
    assert scenario_count == 1
    assert role_count == 3
