from __future__ import annotations

import math

import pytest

from peopleops.forecast import annual_to_monthly_attrition, forecast_workforce
from peopleops.models import InputValidationError, RolePlan, Scenario


def make_scenario(role: RolePlan, *, budget: float = 1_000.0, capacity=(10, 10, 10, 10, 10, 10)) -> Scenario:
    return Scenario(roles=(role,), hiring_budget=budget, recruiting_capacity=capacity)


def test_9_attrition_conversion_and_manual_forecast() -> None:
    annual = 0.12
    monthly = annual_to_monthly_attrition(annual)
    assert monthly == pytest.approx(1 - 0.88 ** (1 / 12))

    role = RolePlan(
        department="Operations",
        role="Coordinator",
        current_fte=10.0,
        annual_attrition_rate=annual,
        staffing_targets=(0.0,) * 6,
        hiring_lead_time=0,
        monthly_loaded_cost=100.0,
        in_flight_hires={1: 1},
    )
    result = forecast_workforce(make_scenario(role))
    values = result.by_role[role.key].expected_fte
    month_1 = 10.0 * (1 - monthly)
    month_2 = month_1 * (1 - monthly) + 1.0
    assert values[0] == pytest.approx(month_1)
    assert values[1] == pytest.approx(month_2)
    assert values[2] == pytest.approx(month_2 * (1 - monthly))


@pytest.mark.parametrize(
    "role_kwargs, scenario_kwargs",
    [
        ({"current_fte": -0.1}, {}),
        ({"staffing_targets": (1, 1, -1, 1, 1, 1)}, {}),
        ({"annual_attrition_rate": -0.01}, {}),
        ({"annual_attrition_rate": 1.0}, {}),
        ({"hiring_lead_time": -1}, {}),
        ({"monthly_loaded_cost": -1.0}, {}),
        ({}, {"budget": -1.0}),
        ({}, {"capacity": (1, 1, -1, 1, 1, 1)}),
        ({}, {"capacity": (1, 1, 1, 1, 1, 1.5)}),
    ],
)
def test_10_input_validation_rejects_invalid_contract_values(role_kwargs, scenario_kwargs) -> None:
    values = {
        "department": "Engineering",
        "role": "Engineer",
        "current_fte": 1.0,
        "annual_attrition_rate": 0.0,
        "staffing_targets": (1.0,) * 6,
        "hiring_lead_time": 0,
        "monthly_loaded_cost": 100.0,
    }
    values.update(role_kwargs)
    if role_kwargs:
        with pytest.raises(InputValidationError):
            RolePlan(**values)
        return

    role = RolePlan(**values)
    with pytest.raises(InputValidationError):
        make_scenario(role, **scenario_kwargs)


def test_forecast_rejects_hire_arriving_beyond_horizon() -> None:
    role = RolePlan(
        department="Engineering",
        role="Engineer",
        current_fte=0.0,
        annual_attrition_rate=0.0,
        staffing_targets=(1.0,) * 6,
        hiring_lead_time=6,
        monthly_loaded_cost=100.0,
    )
    with pytest.raises(InputValidationError):
        forecast_workforce(make_scenario(role), {(role.key, 0): 1})
