"""Deterministic expected-FTE forecasting for the M1 contract."""

from __future__ import annotations

from math import isfinite
from numbers import Real
from typing import Dict, Mapping, Optional

from .models import ForecastResult, HireKey, InputValidationError, RoleForecast, Scenario


def annual_to_monthly_attrition(annual_rate: float) -> float:
    """Convert annual attrition to its equivalent monthly compound rate.

    The rate is an expected fractional FTE reduction. It is not a probability
    simulation or a rounding rule for individual employees.
    """
    if isinstance(annual_rate, bool) or not isinstance(annual_rate, Real):
        raise InputValidationError("annual_attrition_rate must be a finite number in [0, 1).")
    annual = float(annual_rate)
    if not isfinite(annual) or annual < 0 or annual >= 1:
        raise InputValidationError("annual_attrition_rate must be in [0, 1).")
    return 1 - (1 - annual) ** (1 / 12)


def _validated_hires(
    scenario: Scenario, planned_hires: Optional[Mapping[HireKey, int]]
) -> Dict[HireKey, int]:
    hires: Dict[HireKey, int] = {}
    if planned_hires is None:
        return hires

    roles = {role.key: role for role in scenario.roles}
    for (role_key, decision_month), quantity in planned_hires.items():
        if role_key not in roles:
            raise InputValidationError(f"Unknown role in planned_hires: {role_key!r}.")
        if isinstance(decision_month, bool) or not isinstance(decision_month, int):
            raise InputValidationError("planned_hires decision month must be an integer.")
        if decision_month < 0 or decision_month >= scenario.horizon_months:
            raise InputValidationError("planned_hires decision month is outside the planning horizon.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise InputValidationError("planned_hires quantity must be a nonnegative integer.")
        arrival = decision_month + roles[role_key].hiring_lead_time
        if quantity and arrival >= scenario.horizon_months:
            raise InputValidationError(
                "planned_hires cannot contain a hire whose arrival is outside the planning horizon."
            )
        hires[(role_key, decision_month)] = quantity
    return hires


def forecast_workforce(
    scenario: Scenario, planned_hires: Optional[Mapping[HireKey, int]] = None
) -> ForecastResult:
    """Forecast expected FTE and shortages under a specified hiring plan.

    For month *m*, expected FTE equals prior expected FTE after attrition plus
    in-flight and newly-arriving planned hires. Arrivals do not attrit in their
    arrival month because attrition is applied to the prior month's workforce.
    """
    hires = _validated_hires(scenario, planned_hires)
    by_role: Dict[str, RoleForecast] = {}

    for role in scenario.roles:
        monthly_attrition = annual_to_monthly_attrition(role.annual_attrition_rate)
        expected = role.current_fte
        expected_values = []
        shortage_values = []
        for month in range(scenario.horizon_months):
            arriving_planned = sum(
                quantity
                for (role_key, decision_month), quantity in hires.items()
                if role_key == role.key and decision_month + role.hiring_lead_time == month
            )
            expected = (
                expected * (1 - monthly_attrition)
                + role.in_flight_hires.get(month, 0)
                + arriving_planned
            )
            expected_values.append(expected)
            shortage_values.append(max(role.staffing_targets[month] - expected, 0.0))
        by_role[role.key] = RoleForecast(
            expected_fte=tuple(expected_values), shortages=tuple(shortage_values)
        )
    return ForecastResult(by_role=by_role)
