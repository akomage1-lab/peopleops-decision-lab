"""M6 transient scenario service and API contract tests."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from api.app.forecast_service import production_baseline_forecast
from api.app.models import WorkforceRoleRecord
from api.app.optimization_service import (
    ProductionRoleOverride,
    assemble_production_optimization_inputs,
    forecast_production_scenario,
    optimize_production_workforce,
)
from peopleops.forecast import forecast_workforce
from peopleops.optimizer import PRIMARY_OBJECTIVE_TOLERANCE, optimize_hiring_plan


def _sdr_override(session) -> ProductionRoleOverride:
    role = session.scalar(
        select(WorkforceRoleRecord).where(
            WorkforceRoleRecord.name == "Sales Development Representative"
        )
    )
    assert role is not None
    return ProductionRoleOverride(
        role_id=role.id,
        annual_expected_attrition_rate=0.18,
        staffing_targets=(20.0, 20.0, 21.0, 21.0, 22.0, 22.0),
    )


def test_m6_scenario_forecast_applies_overrides_without_mutating_persisted_baseline(session_factory) -> None:
    with session_factory() as session:
        baseline = production_baseline_forecast(session)
        override = _sdr_override(session)
        role = session.get(WorkforceRoleRecord, override.role_id)
        assert role is not None
        persisted_attrition = role.annual_expected_attrition_rate
        persisted_targets = tuple(item.staffing_target for item in role.planning_assumptions)
        scenario = forecast_production_scenario(session, (override,))
        january = next(
            row for row in scenario.role_months
            if row.role_id == override.role_id and row.month == date(2026, 1, 1)
        )
        baseline_january = next(
            row for row in baseline.role_months
            if row.role_id == override.role_id and row.month == date(2026, 1, 1)
        )
        assert january.expected_fte < baseline_january.expected_fte
        assert january.staffing_target == pytest.approx(20.0)
        session.expire_all()
        unchanged_role = session.get(WorkforceRoleRecord, override.role_id)
        assert unchanged_role is not None
        assert unchanged_role.annual_expected_attrition_rate == persisted_attrition
        assert tuple(item.staffing_target for item in unchanged_role.planning_assumptions) == persisted_targets


def test_m6_empty_scenario_is_equivalent_to_persisted_m4_baseline(session_factory) -> None:
    with session_factory() as session:
        baseline = production_baseline_forecast(session)
        scenario = forecast_production_scenario(session, ())
    baseline_rows = {(row.role_id, row.month): row for row in baseline.role_months}
    assert scenario.total_understaffed_fte_months == pytest.approx(
        baseline.total_understaffed_fte_months,
        rel=0,
        abs=PRIMARY_OBJECTIVE_TOLERANCE,
    )
    for row in scenario.role_months:
        persisted = baseline_rows[(row.role_id, row.month)]
        assert row.expected_fte == pytest.approx(
            persisted.expected_fte, rel=0, abs=PRIMARY_OBJECTIVE_TOLERANCE
        )
        assert row.staffing_target == pytest.approx(
            persisted.staffing_target, rel=0, abs=PRIMARY_OBJECTIVE_TOLERANCE
        )


def test_m6_scenario_optimizer_matches_direct_m1_and_respects_constraints(session_factory) -> None:
    with session_factory() as session:
        override = _sdr_override(session)
        assembly = assemble_production_optimization_inputs(
            session, 150_000.0, [2] * 6, (override,)
        )
        direct_baseline = forecast_workforce(assembly.scenario)
        direct_optimized = optimize_hiring_plan(assembly.scenario)
        production = optimize_production_workforce(session, 150_000.0, [2] * 6, (override,))
    assert production.baseline_understaffed_fte_months == pytest.approx(
        direct_baseline.total_understaffed_fte_months,
        rel=0,
        abs=PRIMARY_OBJECTIVE_TOLERANCE,
    )
    assert production.optimized_understaffed_fte_months == pytest.approx(
        direct_optimized.total_understaffed_fte_months,
        rel=0,
        abs=PRIMARY_OBJECTIVE_TOLERANCE,
    )
    assert production.planning_period_incremental_workforce_spend_used <= 150_000.0
    assert all(1 <= item.arrival_month <= 6 for item in production.recommendations)


def test_m6_scenario_api_matches_service_and_does_not_persist(client, session_factory) -> None:
    with session_factory() as session:
        override = _sdr_override(session)
        direct = forecast_production_scenario(session, (override,))
    payload = {
        "role_overrides": [{
            "role_id": override.role_id,
            "annual_expected_attrition_rate": override.annual_expected_attrition_rate,
            "staffing_targets": list(override.staffing_targets or ()),
        }]
    }
    response = client.post("/api/workforce/scenario/forecast", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["total_understaffed_fte_months"] == pytest.approx(
        direct.total_understaffed_fte_months
    )
    with session_factory() as session:
        role = session.get(WorkforceRoleRecord, override.role_id)
        assert role is not None
        assert role.annual_expected_attrition_rate == pytest.approx(0.12)


def test_m6_scenario_optimize_api_uses_transient_assumptions(client, session_factory) -> None:
    with session_factory() as session:
        override = _sdr_override(session)
        direct = optimize_production_workforce(session, 150_000.0, [2] * 6, (override,))
    response = client.post(
        "/api/workforce/scenario/optimize",
        json={
            "planning_period_incremental_workforce_budget": 150_000.0,
            "monthly_recruiting_capacity": [2] * 6,
            "role_overrides": [{
                "role_id": override.role_id,
                "annual_expected_attrition_rate": override.annual_expected_attrition_rate,
                "staffing_targets": list(override.staffing_targets or ()),
            }],
        },
    )
    assert response.status_code == 200
    assert response.json()["optimized_understaffed_fte_months"] == pytest.approx(
        direct.optimized_understaffed_fte_months
    )


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/workforce/scenario/forecast", {"role_overrides": [{"role_id": 5, "annual_expected_attrition_rate": 1.0}]}),
        ("/api/workforce/scenario/forecast", {"role_overrides": [{"role_id": 5, "staffing_targets": [1, 1, 1, 1, 1, -1]}]}),
        ("/api/workforce/scenario/forecast", {"role_overrides": [{"role_id": 5}]}),
        ("/api/workforce/scenario/forecast", {"role_overrides": [{"role_id": 99999, "annual_expected_attrition_rate": 0.1}]}),
        ("/api/workforce/scenario/optimize", {"planning_period_incremental_workforce_budget": -1, "monthly_recruiting_capacity": [2] * 6, "role_overrides": []}),
    ],
)
def test_m6_scenario_api_rejects_invalid_inputs(client, path, payload) -> None:
    assert client.post(path, json=payload).status_code == 422
