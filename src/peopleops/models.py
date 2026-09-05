"""Validated aggregate workforce-planning inputs and result data."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from numbers import Real
from typing import Dict, Mapping, Tuple


HORIZON_MONTHS = 6
HireKey = Tuple[str, int]


class InputValidationError(ValueError):
    """Raised when a scenario would violate the frozen M1 input contract."""


def _finite_number(value: object, field_name: str, *, nonnegative: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        raise InputValidationError(f"{field_name} must be a finite number.")
    number = float(value)
    if nonnegative and number < 0:
        raise InputValidationError(f"{field_name} must be nonnegative.")
    return number


def _nonnegative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InputValidationError(f"{field_name} must be a nonnegative integer.")
    return value


@dataclass(frozen=True)
class RolePlan:
    """Aggregate workforce state and assumptions for one department × role."""

    department: str
    role: str
    current_fte: float
    annual_attrition_rate: float
    staffing_targets: Tuple[float, ...]
    hiring_lead_time: int
    monthly_loaded_cost: float
    in_flight_hires: Mapping[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.department, str) or not self.department.strip():
            raise InputValidationError("department must be a non-empty string.")
        if not isinstance(self.role, str) or not self.role.strip():
            raise InputValidationError("role must be a non-empty string.")
        _finite_number(self.current_fte, "current_fte")
        annual_rate = _finite_number(
            self.annual_attrition_rate, "annual_attrition_rate", nonnegative=True
        )
        if annual_rate >= 1:
            raise InputValidationError("annual_attrition_rate must be in [0, 1).")
        _nonnegative_integer(self.hiring_lead_time, "hiring_lead_time")
        _finite_number(self.monthly_loaded_cost, "monthly_loaded_cost")

        targets = tuple(self.staffing_targets)
        for month, target in enumerate(targets):
            _finite_number(target, f"staffing_targets[{month}]")
        object.__setattr__(self, "staffing_targets", targets)

        in_flight = dict(self.in_flight_hires)
        for arrival_month, hires in in_flight.items():
            _nonnegative_integer(arrival_month, "in_flight_hires arrival month")
            _nonnegative_integer(hires, f"in_flight_hires[{arrival_month}]")
        object.__setattr__(self, "in_flight_hires", in_flight)

    @property
    def key(self) -> str:
        """Stable display key for this department × role combination."""
        return f"{self.department} / {self.role}"


@dataclass(frozen=True)
class Scenario:
    """A six-month aggregate planning scenario for M1."""

    roles: Tuple[RolePlan, ...]
    hiring_budget: float
    recruiting_capacity: Tuple[int, ...]
    horizon_months: int = HORIZON_MONTHS

    def __post_init__(self) -> None:
        if self.horizon_months != HORIZON_MONTHS:
            raise InputValidationError(
                f"M1 fixes the planning horizon at {HORIZON_MONTHS} months."
            )
        roles = tuple(self.roles)
        if not roles:
            raise InputValidationError("scenario must contain at least one role.")
        if len({role.key for role in roles}) != len(roles):
            raise InputValidationError("department / role combinations must be unique.")
        for role in roles:
            if len(role.staffing_targets) != self.horizon_months:
                raise InputValidationError(
                    f"{role.key} must provide exactly {self.horizon_months} staffing targets."
                )
            for arrival_month in role.in_flight_hires:
                if arrival_month >= self.horizon_months:
                    raise InputValidationError(
                        f"{role.key} in-flight hire arrival must be inside the planning horizon."
                    )
        object.__setattr__(self, "roles", roles)

        _finite_number(self.hiring_budget, "hiring_budget")
        capacity = tuple(self.recruiting_capacity)
        if len(capacity) != self.horizon_months:
            raise InputValidationError(
                f"recruiting_capacity must contain {self.horizon_months} monthly values."
            )
        for month, limit in enumerate(capacity):
            _nonnegative_integer(limit, f"recruiting_capacity[{month}]")
        object.__setattr__(self, "recruiting_capacity", capacity)


@dataclass(frozen=True)
class RoleForecast:
    """Expected FTE and the resulting shortage for each month of one role."""

    expected_fte: Tuple[float, ...]
    shortages: Tuple[float, ...]


@dataclass(frozen=True)
class ForecastResult:
    """Role-level forecast outputs plus a transparent aggregate shortage metric."""

    by_role: Mapping[str, RoleForecast]

    @property
    def total_understaffed_fte_months(self) -> float:
        return sum(sum(role.shortages) for role in self.by_role.values())


@dataclass(frozen=True)
class HiringRecommendation:
    """A nonzero optimized hiring start and its in-horizon arrival/cost impact."""

    role_key: str
    decision_month: int
    hires: int
    arrival_month: int
    incremental_cost: float


@dataclass(frozen=True)
class OptimizationResult:
    """A verified lexicographic optimization result."""

    solver_name: str
    primary_status: str
    secondary_status: str
    recommendations: Tuple[HiringRecommendation, ...]
    forecast: ForecastResult
    budget_used: float
    primary_optimum: float

    @property
    def total_understaffed_fte_months(self) -> float:
        return self.forecast.total_understaffed_fte_months

    @property
    def termination_status(self) -> str:
        return f"primary={self.primary_status}; secondary={self.secondary_status}"
