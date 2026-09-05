from __future__ import annotations

import pytest

from peopleops.forecast import forecast_workforce
from peopleops.models import RolePlan, Scenario
from peopleops.optimizer import PRIMARY_OBJECTIVE_TOLERANCE, optimize_hiring_plan


def role(
    name: str,
    *,
    current: float = 0.0,
    target=(1.0,) * 6,
    lead: int = 0,
    cost: float = 100.0,
    department: str = "Department",
) -> RolePlan:
    return RolePlan(
        department=department,
        role=name,
        current_fte=current,
        annual_attrition_rate=0.0,
        staffing_targets=target,
        hiring_lead_time=lead,
        monthly_loaded_cost=cost,
    )


def scenario(
    roles, *, budget: float = 100_000.0, capacity=(10, 10, 10, 10, 10, 10)
) -> Scenario:
    return Scenario(roles=tuple(roles), hiring_budget=budget, recruiting_capacity=capacity)


def result_plan(result):
    return {(item.role_key, item.decision_month): item.hires for item in result.recommendations}


def test_1_no_shortage_requires_no_optimized_hires() -> None:
    plan = role("Stable", current=5.0, target=(5.0,) * 6)
    result = optimize_hiring_plan(scenario((plan,)))
    assert result.recommendations == ()
    assert result.total_understaffed_fte_months == pytest.approx(0.0)
    assert result.termination_status == "primary=OPTIMAL; secondary=OPTIMAL"


def test_2_simple_shortage_hires_the_exact_needed_amount_without_overhiring() -> None:
    plan = role("Needed", current=0.0, target=(2.0,) * 6)
    result = optimize_hiring_plan(scenario((plan,)))
    assert result_plan(result) == {(plan.key, 0): 2}
    assert result.total_understaffed_fte_months == pytest.approx(0.0)
    assert result.budget_used == pytest.approx(1_200.0)


def test_3_zero_budget_leaves_shortage_and_recommends_no_hires() -> None:
    plan = role("Unfunded", target=(2.0,) * 6)
    result = optimize_hiring_plan(scenario((plan,), budget=0.0))
    assert result.recommendations == ()
    assert result.total_understaffed_fte_months == pytest.approx(12.0)


def test_4_lead_time_outside_horizon_has_no_meaningless_decisions() -> None:
    plan = role("TooLate", target=(1.0,) * 6, lead=6)
    result = optimize_hiring_plan(scenario((plan,)))
    assert result.recommendations == ()
    assert result.total_understaffed_fte_months == pytest.approx(6.0)


def test_5_recruiting_capacity_is_never_exceeded() -> None:
    plan = role("CapacityBound", target=(3.0,) * 6)
    capacity = (1, 1, 1, 1, 1, 1)
    result = optimize_hiring_plan(scenario((plan,), capacity=capacity))
    by_month = [0] * 6
    for recommendation in result.recommendations:
        by_month[recommendation.decision_month] += recommendation.hires
    assert all(starts <= capacity[month] for month, starts in enumerate(by_month))
    assert by_month[:3] == [1, 1, 1]


def test_6_limited_budget_selects_allocation_with_lower_understaffing() -> None:
    high_value = role("Core", target=(1.0,) * 6, department="Engineering")
    low_value = role(
        "LateNeed", target=(0.0, 0.0, 0.0, 0.0, 0.0, 0.5), department="Support"
    )
    limited = scenario((high_value, low_value), budget=600.0)
    result = optimize_hiring_plan(limited)
    assert result_plan(result) == {(high_value.key, 0): 1}
    assert result.total_understaffed_fte_months == pytest.approx(0.5)
    assert result.total_understaffed_fte_months < forecast_workforce(limited).total_understaffed_fte_months


def test_7_cost_tiebreaker_selects_lower_cost_plan_at_equal_minimum_shortage() -> None:
    expensive = role(
        "Expensive", target=(0.0, 0.0, 0.0, 0.0, 0.0, 1.0), cost=100.0, department="A"
    )
    cheap = role(
        "Cheap", target=(0.0, 0.0, 0.0, 0.0, 0.0, 1.0), cost=10.0, department="B"
    )
    tie = scenario((expensive, cheap), capacity=(0, 0, 0, 0, 0, 1))
    result = optimize_hiring_plan(tie)
    assert result.total_understaffed_fte_months == pytest.approx(1.0)
    assert result_plan(result) == {(cheap.key, 5): 1}
    assert result.budget_used == pytest.approx(10.0)


def test_8_longer_lead_time_cannot_improve_shortage_or_arrive_early() -> None:
    immediate = role("Immediate", lead=0)
    delayed = role("Delayed", lead=2)
    immediate_result = optimize_hiring_plan(scenario((immediate,)))
    delayed_result = optimize_hiring_plan(scenario((delayed,)))
    assert delayed_result.total_understaffed_fte_months >= immediate_result.total_understaffed_fte_months
    assert delayed_result.total_understaffed_fte_months == pytest.approx(2.0)
    forecast = delayed_result.forecast.by_role[delayed.key]
    assert forecast.expected_fte[0] == pytest.approx(0.0)
    assert forecast.expected_fte[1] == pytest.approx(0.0)
    assert forecast.expected_fte[2] == pytest.approx(1.0)


def test_adversarial_more_budget_cannot_worsen_optimal_understaffing() -> None:
    plan = role("BudgetMonotonic", target=(1.0,) * 6)
    constrained = optimize_hiring_plan(scenario((plan,), budget=0.0))
    expanded = optimize_hiring_plan(scenario((plan,), budget=600.0))
    assert expanded.total_understaffed_fte_months <= constrained.total_understaffed_fte_months


def test_adversarial_more_recruiting_capacity_cannot_worsen_optimal_understaffing() -> None:
    plan = role("CapacityMonotonic", target=(3.0,) * 6)
    constrained = optimize_hiring_plan(scenario((plan,), capacity=(0, 0, 0, 0, 0, 0)))
    expanded = optimize_hiring_plan(scenario((plan,), capacity=(3, 3, 3, 3, 3, 3)))
    assert expanded.total_understaffed_fte_months <= constrained.total_understaffed_fte_months


def test_adversarial_lead_time_cannot_create_coverage_before_arrival_without_budget_binding() -> None:
    immediate = role("ImmediateCoverage", lead=0)
    delayed = role("DelayedCoverage", lead=2)
    unrestricted_budget = 100_000.0
    immediate_result = optimize_hiring_plan(scenario((immediate,), budget=unrestricted_budget))
    delayed_scenario = scenario((delayed,), budget=unrestricted_budget)
    delayed_baseline = forecast_workforce(delayed_scenario)
    delayed_result = optimize_hiring_plan(delayed_scenario)

    assert delayed_result.budget_used < unrestricted_budget
    assert delayed_result.total_understaffed_fte_months >= immediate_result.total_understaffed_fte_months
    delayed_forecast = delayed_result.forecast.by_role[delayed.key]
    baseline_forecast = delayed_baseline.by_role[delayed.key]
    assert delayed_forecast.expected_fte[:2] == pytest.approx(baseline_forecast.expected_fte[:2])
    assert delayed_forecast.expected_fte[:2] == pytest.approx((0.0, 0.0))


def test_adversarial_output_is_feasible_and_never_worse_than_zero_hire_baseline() -> None:
    sales = role("Sales", current=0.0, target=(2.0,) * 6, cost=125.0, department="Sales")
    support = role(
        "Support", current=0.0, target=(0.0, 1.0, 1.0, 1.0, 1.0, 1.0), lead=1,
        cost=80.0, department="Support",
    )
    audit_scenario = scenario(
        (sales, support), budget=1_000.0, capacity=(1, 1, 1, 1, 1, 1)
    )
    baseline = forecast_workforce(audit_scenario)
    result = optimize_hiring_plan(audit_scenario)

    assert result.total_understaffed_fte_months <= baseline.total_understaffed_fte_months
    assert result.total_understaffed_fte_months <= (
        result.primary_optimum + PRIMARY_OBJECTIVE_TOLERANCE
    )
    assert result.budget_used <= audit_scenario.hiring_budget
    monthly_starts = [0] * audit_scenario.horizon_months
    for recommendation in result.recommendations:
        assert 0 <= recommendation.arrival_month < audit_scenario.horizon_months
        monthly_starts[recommendation.decision_month] += recommendation.hires
    assert all(
        starts <= audit_scenario.recruiting_capacity[month]
        for month, starts in enumerate(monthly_starts)
    )


def test_adversarial_month_six_arrival_has_one_month_cost_and_must_create_benefit() -> None:
    last_month_need = role(
        "LastMonthNeed", target=(0.0, 0.0, 0.0, 0.0, 0.0, 1.0), lead=1, cost=100.0
    )
    last_month_scenario = scenario(
        (last_month_need,), budget=100.0, capacity=(0, 0, 0, 0, 1, 0)
    )
    baseline = forecast_workforce(last_month_scenario)
    result = optimize_hiring_plan(last_month_scenario)

    assert baseline.total_understaffed_fte_months == pytest.approx(1.0)
    assert result_plan(result) == {(last_month_need.key, 4): 1}
    recommendation = result.recommendations[0]
    assert recommendation.arrival_month == 5
    assert recommendation.incremental_cost == pytest.approx(100.0)
    assert result.total_understaffed_fte_months == pytest.approx(0.0)
    assert all(
        item.arrival_month < last_month_scenario.horizon_months
        for item in result.recommendations
    )
