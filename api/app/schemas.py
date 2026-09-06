"""Typed public request and response contracts for the M2/M3 API surface."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScenarioRoleResponse(BaseModel):
    """Read-only role assumptions displayed as part of a seeded scenario."""

    model_config = ConfigDict(from_attributes=True)

    department: str
    role: str
    current_fte: float
    annual_attrition_rate: float
    staffing_targets: List[float]
    hiring_lead_time: int
    monthly_loaded_cost: float
    in_flight_hires: dict[str, int]


class ScenarioResponse(BaseModel):
    """The limited M2 scenario payload fetched by the one-page UI."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    planning_horizon_months: int
    planning_period_incremental_workforce_budget: float
    recruiting_capacity: List[int]
    roles: List[ScenarioRoleResponse]


class OptimizeRequest(BaseModel):
    """Optional transient budget override; it never persists in M2."""

    planning_period_incremental_workforce_budget: Optional[float] = Field(
        default=None, ge=0
    )


class RecommendationResponse(BaseModel):
    """Human-facing, one-based start and arrival months for one hiring decision."""

    department: str
    role: str
    decision_month: int
    arrival_month: int
    hires: int
    incremental_workforce_spend: float


class SolverStatusResponse(BaseModel):
    """Safe solver summary; raw solver model internals are intentionally omitted."""

    solver: str
    primary: str
    secondary: str


class OptimizeResponse(BaseModel):
    """The complete M2 optimization result consumed by the browser."""

    scenario_id: int
    available_budget: float
    baseline_understaffed_fte_months: float
    optimized_understaffed_fte_months: float
    improvement_understaffed_fte_months: float
    incremental_workforce_spend_used: float
    recommendations: List[RecommendationResponse]
    solver_status: SolverStatusResponse


class DepartmentMetricResponse(BaseModel):
    department: str
    current_fte: float
    staffing_target: float
    staffing_gap: float
    hires: int
    exits: int
    attrition_rate: Optional[float]


class WorkforceSummaryResponse(BaseModel):
    as_of_month: date
    historical_start_month: date
    historical_end_month: date
    current_total_fte: float
    total_staffing_target: float
    total_staffing_gap: float
    hires: int
    exits: int
    attrition_rate: Optional[float]
    average_hiring_lead_time_days: Optional[float]
    median_hiring_lead_time_days: Optional[float]
    departments: List[DepartmentMetricResponse]


class WorkforceHistoryPointResponse(BaseModel):
    month: date
    total_fte: float
    hires: int
    exits: int


class RoleForecastProvenanceResponse(BaseModel):
    department: str
    role: str
    observation_date: date
    starting_observed_fte: float
    annual_expected_attrition_rate: float
    staffing_targets: List[float]
    in_flight_hires: List[int]


class RoleForecastMonthResponse(BaseModel):
    department: str
    role: str
    month: date
    expected_fte_before_attrition: float
    expected_attrition_loss: float
    in_flight_hires_arriving: int
    expected_fte: float
    staffing_target: float
    staffing_shortage: float
    staffing_surplus: float


class DepartmentForecastMonthResponse(BaseModel):
    department: str
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


class OrganizationForecastMonthResponse(BaseModel):
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


class ProductionForecastResponse(BaseModel):
    generated_at: datetime
    model_version: str
    planning_horizon_months: int
    observation_date: date
    role_provenance: List[RoleForecastProvenanceResponse]
    role_months: List[RoleForecastMonthResponse]
    department_months: List[DepartmentForecastMonthResponse]
    organization_months: List[OrganizationForecastMonthResponse]
