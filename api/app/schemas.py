"""Typed public request and response contracts for the M2/M3 API surface."""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    role_id: int
    department_id: int
    department: str
    role: str
    observation_date: date
    starting_observed_fte: float
    annual_expected_attrition_rate: float
    staffing_targets: List[float]
    in_flight_hires: List[int]


class RoleForecastMonthResponse(BaseModel):
    role_id: int
    department_id: int
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
    total_understaffed_fte_months: float


class ProductionOptimizeRequest(BaseModel):
    """Explicit, transient organization-wide constraints for a production solve."""

    planning_period_incremental_workforce_budget: float = Field(ge=0)
    monthly_recruiting_capacity: List[int] = Field(min_length=6, max_length=6)

    @field_validator("planning_period_incremental_workforce_budget")
    @classmethod
    def budget_must_be_finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("planning_period_incremental_workforce_budget must be finite.")
        return value

    @field_validator("monthly_recruiting_capacity")
    @classmethod
    def capacities_must_be_nonnegative(cls, values: List[int]) -> List[int]:
        if any(capacity < 0 for capacity in values):
            raise ValueError("monthly_recruiting_capacity values must be nonnegative.")
        return values


class ProductionOptimizationRoleMonthResponse(BaseModel):
    role_id: int
    department_id: int
    department: str
    role: str
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


class ProductionOptimizationDepartmentMonthResponse(BaseModel):
    department_id: int
    department: str
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


class ProductionOptimizationOrganizationMonthResponse(BaseModel):
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


class ProductionHiringRecommendationResponse(BaseModel):
    role_id: int
    department_id: int
    department: str
    role: str
    hires: int
    decision_month: int
    arrival_month: int
    planning_period_incremental_workforce_spend: float


class ProductionOptimizeResponse(BaseModel):
    generated_at: datetime
    model_version: str
    observation_date: date
    planning_horizon_months: int
    submitted_budget: float
    submitted_monthly_recruiting_capacity: List[int]
    solver: str
    primary_status: str
    secondary_status: str
    optimization_duration_ms: float
    baseline_understaffed_fte_months: float
    baseline_role_months: List[ProductionOptimizationRoleMonthResponse]
    baseline_department_months: List[ProductionOptimizationDepartmentMonthResponse]
    baseline_organization_months: List[ProductionOptimizationOrganizationMonthResponse]
    optimized_understaffed_fte_months: float
    improvement_understaffed_fte_months: float
    planning_period_incremental_workforce_spend_used: float
    unused_budget: float
    recommendations: List[ProductionHiringRecommendationResponse]
    optimized_role_months: List[ProductionOptimizationRoleMonthResponse]
    optimized_department_months: List[ProductionOptimizationDepartmentMonthResponse]
    optimized_organization_months: List[ProductionOptimizationOrganizationMonthResponse]


class ScenarioRoleOverrideRequest(BaseModel):
    """One explicit, transient role-level scenario change."""

    role_id: int = Field(gt=0)
    annual_expected_attrition_rate: Optional[float] = Field(default=None, ge=0, lt=1)
    staffing_targets: Optional[List[float]] = Field(default=None, min_length=6, max_length=6)

    @field_validator("annual_expected_attrition_rate")
    @classmethod
    def attrition_must_be_finite(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not isfinite(value):
            raise ValueError("annual_expected_attrition_rate must be finite.")
        return value

    @field_validator("staffing_targets")
    @classmethod
    def targets_must_be_finite_and_nonnegative(
        cls, values: Optional[List[float]]
    ) -> Optional[List[float]]:
        if values is not None and any(not isfinite(value) or value < 0 for value in values):
            raise ValueError("staffing_targets must contain finite nonnegative values.")
        return values

    @model_validator(mode="after")
    def must_change_an_assumption(self) -> "ScenarioRoleOverrideRequest":
        if self.annual_expected_attrition_rate is None and self.staffing_targets is None:
            raise ValueError("A scenario role override must include attrition or staffing targets.")
        return self


class ProductionScenarioForecastRequest(BaseModel):
    role_overrides: List[ScenarioRoleOverrideRequest] = Field(default_factory=list)


class ProductionScenarioOptimizeRequest(ProductionOptimizeRequest):
    role_overrides: List[ScenarioRoleOverrideRequest] = Field(default_factory=list)


class ProductionScenarioForecastResponse(BaseModel):
    generated_at: datetime
    model_version: str
    observation_date: date
    planning_horizon_months: int
    role_months: List[ProductionOptimizationRoleMonthResponse]
    department_months: List[ProductionOptimizationDepartmentMonthResponse]
    organization_months: List[ProductionOptimizationOrganizationMonthResponse]
    total_understaffed_fte_months: float


class OverviewForecastMonthResponse(BaseModel):
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


class OverviewHistoricalTrendResponse(BaseModel):
    month: date
    total_fte: float
    hires: int
    exits: int


class OverviewDepartmentRiskResponse(BaseModel):
    department: str
    current_fte: float
    next_planning_target: float
    current_staffing_gap: float
    total_understaffed_fte_months: float
    end_of_horizon_shortage: float
    recent_attrition_rate: Optional[float]
    recent_exits: int
    recent_hires: int


class OverviewHiringLeadTimeResponse(BaseModel):
    department: str
    role: str
    completed_cycles: int
    average_days: Optional[float]
    median_days: Optional[float]


class WorkforceOverviewResponse(BaseModel):
    generated_at: datetime
    observation_date: date
    next_planning_month: date
    recent_historical_start_month: date
    recent_historical_end_month: date
    current_total_fte: float
    next_planning_target: float
    current_staffing_gap: float
    six_month_understaffed_fte_months: float
    recent_hires: int
    recent_exits: int
    recent_attrition_rate: Optional[float]
    organization_median_time_to_fill_days: Optional[float]
    forecast_months: List[OverviewForecastMonthResponse]
    historical_trend: List[OverviewHistoricalTrendResponse]
    department_risks: List[OverviewDepartmentRiskResponse]
    slowest_filling_roles: List[OverviewHiringLeadTimeResponse]
