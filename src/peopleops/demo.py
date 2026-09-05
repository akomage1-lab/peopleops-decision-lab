"""Runnable synthetic M1 scenario; presentation is intentionally kept here."""

from __future__ import annotations

from .forecast import forecast_workforce
from .models import RolePlan, Scenario
from .optimizer import optimize_hiring_plan


def build_demo_scenario() -> Scenario:
    """Return a small company with attrition, lead-time, budget, and capacity trade-offs."""
    return Scenario(
        roles=(
            RolePlan(
                department="Sales",
                role="Account Executive",
                current_fte=7.0,
                annual_attrition_rate=0.18,
                staffing_targets=(8.0, 8.0, 8.0, 8.0, 8.0, 8.0),
                hiring_lead_time=0,
                monthly_loaded_cost=11_000.0,
            ),
            RolePlan(
                department="Product",
                role="Data Analyst",
                current_fte=3.5,
                annual_attrition_rate=0.12,
                staffing_targets=(4.0, 4.0, 4.0, 4.5, 4.5, 4.5),
                hiring_lead_time=1,
                monthly_loaded_cost=13_000.0,
            ),
            RolePlan(
                department="Customer Support",
                role="Support Specialist",
                current_fte=4.5,
                annual_attrition_rate=0.08,
                staffing_targets=(5.5, 5.5, 5.5, 5.5, 5.5, 5.5),
                hiring_lead_time=2,
                monthly_loaded_cost=8_000.0,
                in_flight_hires={2: 1},
            ),
        ),
        hiring_budget=170_000.0,
        recruiting_capacity=(2, 2, 2, 2, 2, 2),
    )


def _format_currency(value: float) -> str:
    return f"${value:,.0f}"


def main() -> None:
    """Print baseline and optimized results for the deterministic synthetic scenario."""
    scenario = build_demo_scenario()
    baseline = forecast_workforce(scenario)
    result = optimize_hiring_plan(scenario)

    print("PeopleOps Decision Lab — M1 demo")
    print(f"Planning horizon: {scenario.horizon_months} months")
    print(f"Incremental hiring budget: {_format_currency(scenario.hiring_budget)}")
    print("Baseline projected shortages (FTE by month 1–6):")
    for role in scenario.roles:
        shortages = baseline.by_role[role.key].shortages
        print(f"  {role.key}: " + ", ".join(f"{value:.2f}" for value in shortages))
    print(
        "Baseline understaffed FTE-months: "
        f"{baseline.total_understaffed_fte_months:.3f}"
    )
    print("Recommended hiring starts:")
    if not result.recommendations:
        print("  None")
    for recommendation in result.recommendations:
        print(
            f"  Month {recommendation.decision_month + 1}: "
            f"{recommendation.hires} × {recommendation.role_key}; "
            f"arrives month {recommendation.arrival_month + 1}; "
            f"in-horizon cost {_format_currency(recommendation.incremental_cost)}"
        )
    improvement = baseline.total_understaffed_fte_months - result.total_understaffed_fte_months
    print(f"Budget used: {_format_currency(result.budget_used)}")
    print(f"Optimized understaffed FTE-months: {result.total_understaffed_fte_months:.3f}")
    print(f"Improvement versus baseline: {improvement:.3f} understaffed FTE-months")
    print(f"Solver: {result.solver_name}")
    print(f"Solver termination status: {result.termination_status}")


if __name__ == "__main__":
    main()
