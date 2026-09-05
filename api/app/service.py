"""Translate persisted aggregate inputs into the existing M1 decision engine."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from peopleops.forecast import forecast_workforce
from peopleops.models import RolePlan, Scenario
from peopleops.optimizer import OptimizationResult, optimize_hiring_plan

from .models import ScenarioRecord
from .schemas import OptimizeResponse, RecommendationResponse, SolverStatusResponse


def to_engine_scenario(
    record: ScenarioRecord, budget_override: Optional[float] = None
) -> Scenario:
    """Build the M1 `Scenario` directly from PostgreSQL role inputs.

    This is an integration adapter only: it does not forecast, optimize, or
    reinterpret M1 data. The optional budget changes this in-memory run only.
    """
    roles = tuple(
        RolePlan(
            department=role.department,
            role=role.role,
            current_fte=role.current_fte,
            annual_attrition_rate=role.annual_attrition_rate,
            staffing_targets=tuple(float(target) for target in role.staffing_targets),
            hiring_lead_time=role.hiring_lead_time,
            monthly_loaded_cost=role.monthly_loaded_cost,
            in_flight_hires={int(month): int(hires) for month, hires in role.in_flight_hires.items()},
        )
        for role in record.roles
    )
    scenario = Scenario(
        roles=roles,
        hiring_budget=record.planning_period_incremental_workforce_budget,
        recruiting_capacity=tuple(int(capacity) for capacity in record.recruiting_capacity),
        horizon_months=record.planning_horizon_months,
    )
    if budget_override is not None:
        scenario = replace(scenario, hiring_budget=budget_override)
    return scenario


def optimize_record(
    record: ScenarioRecord, budget_override: Optional[float] = None
) -> OptimizeResponse:
    """Run the real M1 baseline forecast and two-pass optimizer for one record."""
    scenario = to_engine_scenario(record, budget_override)
    baseline = forecast_workforce(scenario)
    result: OptimizationResult = optimize_hiring_plan(scenario)
    role_parts = {
        role.key: (role.department, role.role)
        for role in scenario.roles
    }
    recommendations = [
        RecommendationResponse(
            department=role_parts[item.role_key][0],
            role=role_parts[item.role_key][1],
            decision_month=item.decision_month + 1,
            arrival_month=item.arrival_month + 1,
            hires=item.hires,
            incremental_workforce_spend=item.incremental_cost,
        )
        for item in result.recommendations
    ]
    return OptimizeResponse(
        scenario_id=record.id,
        available_budget=scenario.hiring_budget,
        baseline_understaffed_fte_months=baseline.total_understaffed_fte_months,
        optimized_understaffed_fte_months=result.total_understaffed_fte_months,
        improvement_understaffed_fte_months=(
            baseline.total_understaffed_fte_months - result.total_understaffed_fte_months
        ),
        incremental_workforce_spend_used=result.budget_used,
        recommendations=recommendations,
        solver_status=SolverStatusResponse(
            solver=result.solver_name,
            primary=result.primary_status,
            secondary=result.secondary_status,
        ),
    )
