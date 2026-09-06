"""Deterministic M5 production optimizer adapter, API, and invariant tests."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from api.app.forecast_service import production_baseline_forecast
from api.app.models import WorkforceRoleRecord
from api.app.optimization_service import (
    assemble_production_optimization_inputs,
    optimize_production_workforce,
)
from peopleops.optimizer import (
    PRIMARY_OBJECTIVE_TOLERANCE,
    SolverFailure,
    optimize_hiring_plan,
)


CONSTRAINED_BUDGET = 150_000.0
CONSTRAINED_CAPACITY = [2] * 6


def _role_rows_by_display(rows):
    return {(row.department, row.role, row.month): row for row in rows}


def test_m5_baseline_matches_m4_for_every_role_month_and_total(session_factory) -> None:
    with session_factory() as session:
        m4 = production_baseline_forecast(session)
        m5 = optimize_production_workforce(session, CONSTRAINED_BUDGET, CONSTRAINED_CAPACITY)
    m4_rows = _role_rows_by_display(m4.role_months)
    assert len(m5.baseline_role_months) == len(m4.role_months) == 19 * 6
    for row in m5.baseline_role_months:
        m4_row = m4_rows[(row.department, row.role, row.month)]
        assert row.expected_fte == pytest.approx(
            m4_row.expected_fte, rel=0, abs=PRIMARY_OBJECTIVE_TOLERANCE
        )
        assert row.staffing_target == pytest.approx(
            m4_row.staffing_target, rel=0, abs=PRIMARY_OBJECTIVE_TOLERANCE
        )
        assert row.staffing_shortage == pytest.approx(
            m4_row.staffing_shortage, rel=0, abs=PRIMARY_OBJECTIVE_TOLERANCE
        )
    assert m5.baseline_understaffed_fte_months == pytest.approx(
        sum(row.staffing_shortage for row in m4.role_months),
        rel=0,
        abs=PRIMARY_OBJECTIVE_TOLERANCE,
    )


def test_m5_adapter_and_result_match_direct_m1_optimizer(session_factory) -> None:
    with session_factory() as session:
        assembly = assemble_production_optimization_inputs(
            session, CONSTRAINED_BUDGET, CONSTRAINED_CAPACITY
        )
        direct = optimize_hiring_plan(assembly.scenario)
        production = optimize_production_workforce(
            session, CONSTRAINED_BUDGET, CONSTRAINED_CAPACITY
        )
    assert production.optimized_understaffed_fte_months == pytest.approx(
        direct.total_understaffed_fte_months,
        rel=0,
        abs=PRIMARY_OBJECTIVE_TOLERANCE,
    )
    assert production.planning_period_incremental_workforce_spend_used == pytest.approx(
        direct.budget_used
    )
    assert production.primary_status == direct.primary_status == "OPTIMAL"
    assert production.secondary_status == direct.secondary_status == "OPTIMAL"


def test_m5_zero_budget_returns_the_m4_baseline_without_hires(session_factory) -> None:
    with session_factory() as session:
        result = optimize_production_workforce(session, 0.0, CONSTRAINED_CAPACITY)
    assert result.recommendations == ()
    assert result.planning_period_incremental_workforce_spend_used == 0.0
    assert result.optimized_understaffed_fte_months == pytest.approx(
        result.baseline_understaffed_fte_months
    )


def test_m5_returned_plan_respects_budget_capacity_arrivals_and_no_worsening(session_factory) -> None:
    with session_factory() as session:
        result = optimize_production_workforce(session, CONSTRAINED_BUDGET, CONSTRAINED_CAPACITY)
    starts_by_month = [0] * 6
    for recommendation in result.recommendations:
        starts_by_month[recommendation.decision_month - 1] += recommendation.hires
        assert 1 <= recommendation.arrival_month <= 6
        assert recommendation.arrival_month >= recommendation.decision_month
    assert all(starts <= capacity for starts, capacity in zip(starts_by_month, CONSTRAINED_CAPACITY))
    assert result.planning_period_incremental_workforce_spend_used <= CONSTRAINED_BUDGET
    assert result.optimized_understaffed_fte_months <= result.baseline_understaffed_fte_months


def test_m5_budget_and_capacity_monotonicity(session_factory) -> None:
    with session_factory() as session:
        constrained = optimize_production_workforce(session, CONSTRAINED_BUDGET, CONSTRAINED_CAPACITY)
        higher_budget = optimize_production_workforce(session, 400_000.0, CONSTRAINED_CAPACITY)
        higher_capacity = optimize_production_workforce(session, 400_000.0, [3] * 6)
    assert higher_budget.optimized_understaffed_fte_months <= constrained.optimized_understaffed_fte_months
    assert higher_capacity.optimized_understaffed_fte_months <= higher_budget.optimized_understaffed_fte_months


def test_m5_stable_persisted_role_identity_prevents_display_title_collision(session_factory) -> None:
    with session_factory() as session:
        support_lead = session.scalar(
            select(WorkforceRoleRecord).where(WorkforceRoleRecord.name == "Support Team Lead")
        )
        assert support_lead is not None
        support_lead.name = "Account Executive"
        session.flush()
        result = optimize_production_workforce(session, 0.0, CONSTRAINED_CAPACITY)
        matching_rows = [
            row for row in result.baseline_role_months
            if row.role == "Account Executive" and row.month == date(2026, 1, 1)
        ]
        assert len(matching_rows) == 2
        assert len({row.role_id for row in matching_rows}) == 2
        assert len({row.department_id for row in matching_rows}) == 2
        session.rollback()


def test_m5_stored_monthly_cost_maps_one_to_one_to_m1_cost(session_factory) -> None:
    with session_factory() as session:
        assembly = assemble_production_optimization_inputs(
            session, CONSTRAINED_BUDGET, CONSTRAINED_CAPACITY
        )
        records = {record.id: record for record in session.scalars(select(WorkforceRoleRecord))}
    for role in assembly.scenario.roles:
        identity = assembly.role_identities_by_engine_key[role.key]
        assert role.monthly_loaded_cost == pytest.approx(records[identity.role_id].monthly_loaded_cost)


def test_m5_api_matches_authoritative_service(client, session_factory) -> None:
    with session_factory() as session:
        direct = optimize_production_workforce(session, CONSTRAINED_BUDGET, CONSTRAINED_CAPACITY)
    response = client.post(
        "/api/workforce/optimize",
        json={
            "planning_period_incremental_workforce_budget": CONSTRAINED_BUDGET,
            "monthly_recruiting_capacity": CONSTRAINED_CAPACITY,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["submitted_budget"] == CONSTRAINED_BUDGET
    assert body["submitted_monthly_recruiting_capacity"] == CONSTRAINED_CAPACITY
    assert body["baseline_understaffed_fte_months"] == pytest.approx(
        direct.baseline_understaffed_fte_months
    )
    assert body["optimized_understaffed_fte_months"] == pytest.approx(
        direct.optimized_understaffed_fte_months
    )
    assert body["planning_period_incremental_workforce_spend_used"] == pytest.approx(
        direct.planning_period_incremental_workforce_spend_used
    )
    assert body["primary_status"] == body["secondary_status"] == "OPTIMAL"
    assert len(body["optimized_role_months"]) == 19 * 6


@pytest.mark.parametrize(
    "payload",
    [
        {"monthly_recruiting_capacity": CONSTRAINED_CAPACITY},
        {
            "planning_period_incremental_workforce_budget": -1,
            "monthly_recruiting_capacity": CONSTRAINED_CAPACITY,
        },
        {
            "planning_period_incremental_workforce_budget": "NaN",
            "monthly_recruiting_capacity": CONSTRAINED_CAPACITY,
        },
        {
            "planning_period_incremental_workforce_budget": CONSTRAINED_BUDGET,
            "monthly_recruiting_capacity": [2, 2, 2, 2, 2, -1],
        },
    ],
)
def test_m5_api_rejects_invalid_or_missing_decision_constraints(client, payload) -> None:
    assert client.post("/api/workforce/optimize", json=payload).status_code == 422


def test_m5_solver_failure_is_never_returned_as_a_recommendation(client, monkeypatch) -> None:
    def failed_optimizer(_scenario):
        raise SolverFailure("forced M5 failure")

    monkeypatch.setattr("api.app.optimization_service.optimize_hiring_plan", failed_optimizer)
    response = client.post(
        "/api/workforce/optimize",
        json={
            "planning_period_incremental_workforce_budget": CONSTRAINED_BUDGET,
            "monthly_recruiting_capacity": CONSTRAINED_CAPACITY,
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "The production optimizer did not return a proven optimal plan."
