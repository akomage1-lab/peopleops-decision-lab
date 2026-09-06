"""M11 bounded local constraint sensitivity regression tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from api.app.models import WorkforceRoleRecord
from api.app.optimization_service import (
    ProductionOptimizationFailure,
    ProductionRoleOverride,
    optimize_production_workforce,
)
from api.app.sensitivity_service import analyze_constraint_sensitivity
from peopleops.optimizer import PRIMARY_OBJECTIVE_TOLERANCE


def _override(session) -> ProductionRoleOverride:
    role = session.scalar(select(WorkforceRoleRecord).where(WorkforceRoleRecord.name == "Sales Development Representative"))
    assert role is not None
    return ProductionRoleOverride(role_id=role.id, annual_expected_attrition_rate=0.18)


def _assert_monotone(points) -> None:
    assert all(
        later.optimized_understaffed_fte_months
        <= earlier.optimized_understaffed_fte_months + PRIMARY_OBJECTIVE_TOLERANCE
        for earlier, later in zip(points, points[1:])
    )


def test_m11_sensitivity_reuses_proven_optimizer_and_reconciles_submitted_points(session_factory) -> None:
    with session_factory() as session:
        override = _override(session)
        ordinary = optimize_production_workforce(session, 150_000, [2] * 6, (override,))
        sensitivity = analyze_constraint_sensitivity(session, 150_000, [2] * 6, (override,))
    assert [point.budget for point in sensitivity.budget_sensitivity] == [75_000, 112_500, 150_000, 187_500, 225_000]
    assert [point.monthly_recruiting_capacity for point in sensitivity.recruiting_capacity_sensitivity] == [(1,) * 6, (2,) * 6, (3,) * 6]
    submitted_budget = next(point for point in sensitivity.budget_sensitivity if point.budget == 150_000)
    submitted_capacity = next(point for point in sensitivity.recruiting_capacity_sensitivity if point.monthly_recruiting_capacity == (2,) * 6)
    assert submitted_budget.optimized_understaffed_fte_months == pytest.approx(ordinary.optimized_understaffed_fte_months, abs=PRIMARY_OBJECTIVE_TOLERANCE)
    assert submitted_capacity.optimized_understaffed_fte_months == pytest.approx(ordinary.optimized_understaffed_fte_months, abs=PRIMARY_OBJECTIVE_TOLERANCE)
    _assert_monotone(sensitivity.budget_sensitivity)
    _assert_monotone(sensitivity.recruiting_capacity_sensitivity)
    for point in sensitivity.budget_sensitivity:
        assert point.planning_period_incremental_workforce_spend_used <= point.budget + PRIMARY_OBJECTIVE_TOLERANCE
        assert (point.primary_status, point.secondary_status) == ("OPTIMAL", "OPTIMAL")
    assert all((point.primary_status, point.secondary_status) == ("OPTIMAL", "OPTIMAL") for point in sensitivity.recruiting_capacity_sensitivity)


def test_m11_sensitivity_is_deterministic_and_preserves_role_override(session_factory) -> None:
    with session_factory() as session:
        override = _override(session)
        first = analyze_constraint_sensitivity(session, 150_000, [1, 2, 0, 2, 1, 3], (override,))
        second = analyze_constraint_sensitivity(session, 150_000, [1, 2, 0, 2, 1, 3], (override,))
    assert [(item.budget, item.optimized_understaffed_fte_months) for item in first.budget_sensitivity] == pytest.approx([(item.budget, item.optimized_understaffed_fte_months) for item in second.budget_sensitivity])
    assert [item.monthly_recruiting_capacity for item in first.recruiting_capacity_sensitivity] == [(0, 1, 0, 1, 0, 2), (1, 2, 0, 2, 1, 3), (2, 3, 1, 3, 2, 4)]
    assert first.recruiting_capacity_sensitivity[0].monthly_recruiting_capacity_delta == (-1, -1, 0, -1, -1, -1)


def test_m11_sensitivity_deduplicates_zero_budget_and_zero_capacity_points(session_factory) -> None:
    with session_factory() as session:
        result = analyze_constraint_sensitivity(session, 0, [0] * 6)
    assert [point.budget for point in result.budget_sensitivity] == [0]
    assert [point.monthly_recruiting_capacity for point in result.recruiting_capacity_sensitivity] == [(0,) * 6, (1,) * 6]
    assert all(point.planning_period_incremental_workforce_spend_used == 0 for point in result.budget_sensitivity)


def test_m11_sensitivity_api_contract_and_invalid_input(client) -> None:
    response = client.post("/api/workforce/scenario/sensitivity", json={
        "planning_period_incremental_workforce_budget": 150_000,
        "monthly_recruiting_capacity": [2] * 6,
        "role_overrides": [],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["budget_sensitivity"][2]["budget"] == 150_000
    assert body["recruiting_capacity_sensitivity"][1]["monthly_recruiting_capacity"] == [2] * 6
    assert client.post("/api/workforce/scenario/sensitivity", json={
        "planning_period_incremental_workforce_budget": -1,
        "monthly_recruiting_capacity": [2] * 6,
        "role_overrides": [],
    }).status_code == 422


def test_m11_sensitivity_fails_closed_when_a_point_fails(monkeypatch, session_factory) -> None:
    def fail(*_args, **_kwargs):
        raise ProductionOptimizationFailure("solver failed")

    monkeypatch.setattr("api.app.sensitivity_service.optimize_production_workforce", fail)
    with session_factory() as session:
        with pytest.raises(ProductionOptimizationFailure, match="solver failed"):
            analyze_constraint_sensitivity(session, 150_000, [2] * 6)
