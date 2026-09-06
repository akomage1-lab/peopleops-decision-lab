"""Production M5 adapter from persisted workforce data to the M1 optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from time import perf_counter
from typing import Dict, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from peopleops.forecast import forecast_workforce
from peopleops.models import InputValidationError, RolePlan, Scenario
from peopleops.optimizer import (
    PRIMARY_OBJECTIVE_TOLERANCE,
    SolverFailure,
    optimize_hiring_plan,
)

from .forecast_service import ForecastAssembly, ForecastInputError, assemble_forecast_inputs
from .models import DepartmentRecord, WorkforceRoleRecord


MODEL_VERSION = "m1-production-optimizer-v1"


class ProductionOptimizationInputError(ValueError):
    """Raised when production data or submitted decision constraints are invalid."""


class ProductionOptimizationFailure(RuntimeError):
    """Raised when a production optimization result cannot be safely returned."""


@dataclass(frozen=True)
class RoleIdentity:
    role_id: int
    department_id: int
    department: str
    role: str


@dataclass(frozen=True)
class ProductionOptimizationAssembly:
    scenario: Scenario
    planning_months: Tuple[date, ...]
    observation_date: date
    role_identities_by_engine_key: Dict[str, RoleIdentity]


@dataclass(frozen=True)
class ProductionOptimizationRoleMonth:
    role_id: int
    department_id: int
    department: str
    role: str
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


@dataclass(frozen=True)
class ProductionOptimizationDepartmentMonth:
    department_id: int
    department: str
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


@dataclass(frozen=True)
class ProductionOptimizationOrganizationMonth:
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


@dataclass(frozen=True)
class ProductionHiringRecommendation:
    role_id: int
    department_id: int
    department: str
    role: str
    hires: int
    decision_month: int
    arrival_month: int
    planning_period_incremental_workforce_spend: float


@dataclass(frozen=True)
class ProductionOptimizationResult:
    generated_at: datetime
    model_version: str
    observation_date: date
    planning_horizon_months: int
    submitted_budget: float
    submitted_monthly_recruiting_capacity: Tuple[int, ...]
    solver: str
    primary_status: str
    secondary_status: str
    optimization_duration_ms: float
    baseline_understaffed_fte_months: float
    baseline_role_months: Sequence[ProductionOptimizationRoleMonth]
    baseline_department_months: Sequence[ProductionOptimizationDepartmentMonth]
    baseline_organization_months: Sequence[ProductionOptimizationOrganizationMonth]
    optimized_understaffed_fte_months: float
    improvement_understaffed_fte_months: float
    planning_period_incremental_workforce_spend_used: float
    unused_budget: float
    recommendations: Sequence[ProductionHiringRecommendation]
    optimized_role_months: Sequence[ProductionOptimizationRoleMonth]
    optimized_department_months: Sequence[ProductionOptimizationDepartmentMonth]
    optimized_organization_months: Sequence[ProductionOptimizationOrganizationMonth]


def _engine_role_identity(record: WorkforceRoleRecord) -> Tuple[str, str]:
    """Create a stable M1-safe alias; display names never form the solver identity."""
    return (f"department_id:{record.department_id}", f"workforce_role_id:{record.id}")


def assemble_production_optimization_inputs(
    session: Session,
    planning_period_incremental_workforce_budget: float,
    monthly_recruiting_capacity: Sequence[int],
) -> ProductionOptimizationAssembly:
    """Adapt complete M4 inputs to an M1 scenario with stable persisted role IDs."""
    try:
        m4_assembly: ForecastAssembly = assemble_forecast_inputs(session)
    except ForecastInputError as error:
        raise ProductionOptimizationInputError(str(error)) from error
    records = list(
        session.scalars(
            select(WorkforceRoleRecord)
            .join(WorkforceRoleRecord.department)
            .options(selectinload(WorkforceRoleRecord.department))
            .order_by(DepartmentRecord.name, WorkforceRoleRecord.name)
        )
    )
    records_by_display_identity = {
        (record.department.name, record.name): record for record in records
    }
    roles = []
    identities = {}
    for m4_role, provenance in zip(m4_assembly.scenario.roles, m4_assembly.provenance):
        record = records_by_display_identity.get((provenance.department, provenance.role))
        if record is None:
            raise ProductionOptimizationInputError(
                f"Missing persisted role identity for {provenance.department} / {provenance.role}."
            )
        engine_department, engine_role = _engine_role_identity(record)
        role = RolePlan(
            department=engine_department,
            role=engine_role,
            current_fte=m4_role.current_fte,
            annual_attrition_rate=m4_role.annual_attrition_rate,
            staffing_targets=m4_role.staffing_targets,
            hiring_lead_time=m4_role.hiring_lead_time,
            monthly_loaded_cost=m4_role.monthly_loaded_cost,
            in_flight_hires=m4_role.in_flight_hires,
        )
        roles.append(role)
        identities[role.key] = RoleIdentity(
            role_id=record.id,
            department_id=record.department_id,
            department=record.department.name,
            role=record.name,
        )
    try:
        scenario = Scenario(
            roles=tuple(roles),
            hiring_budget=planning_period_incremental_workforce_budget,
            recruiting_capacity=tuple(monthly_recruiting_capacity),
        )
    except InputValidationError as error:
        raise ProductionOptimizationInputError(str(error)) from error
    return ProductionOptimizationAssembly(
        scenario=scenario,
        planning_months=m4_assembly.planning_months,
        observation_date=m4_assembly.observation_date,
        role_identities_by_engine_key=identities,
    )


def _role_months(assembly: ProductionOptimizationAssembly, forecast) -> Tuple[ProductionOptimizationRoleMonth, ...]:
    rows = []
    for role in assembly.scenario.roles:
        identity = assembly.role_identities_by_engine_key[role.key]
        role_forecast = forecast.by_role[role.key]
        for index, month in enumerate(assembly.planning_months):
            rows.append(
                ProductionOptimizationRoleMonth(
                    role_id=identity.role_id,
                    department_id=identity.department_id,
                    department=identity.department,
                    role=identity.role,
                    month=month,
                    expected_fte=role_forecast.expected_fte[index],
                    staffing_target=role.staffing_targets[index],
                    staffing_shortage=role_forecast.shortages[index],
                )
            )
    return tuple(rows)


def _aggregates(
    role_months: Sequence[ProductionOptimizationRoleMonth], planning_months: Sequence[date]
) -> Tuple[
    Tuple[ProductionOptimizationDepartmentMonth, ...],
    Tuple[ProductionOptimizationOrganizationMonth, ...],
]:
    department_rows = []
    organization_rows = []
    for month in planning_months:
        month_rows = [row for row in role_months if row.month == month]
        department_keys = sorted({(row.department_id, row.department) for row in month_rows})
        for department_id, department in department_keys:
            rows = [row for row in month_rows if row.department_id == department_id]
            department_rows.append(
                ProductionOptimizationDepartmentMonth(
                    department_id=department_id,
                    department=department,
                    month=month,
                    expected_fte=sum(row.expected_fte for row in rows),
                    staffing_target=sum(row.staffing_target for row in rows),
                    staffing_shortage=sum(row.staffing_shortage for row in rows),
                )
            )
        organization_rows.append(
            ProductionOptimizationOrganizationMonth(
                month=month,
                expected_fte=sum(row.expected_fte for row in month_rows),
                staffing_target=sum(row.staffing_target for row in month_rows),
                staffing_shortage=sum(row.staffing_shortage for row in month_rows),
            )
        )
    return tuple(department_rows), tuple(organization_rows)


def _validated_recommendations(assembly: ProductionOptimizationAssembly, optimization) -> Tuple[
    Tuple[ProductionHiringRecommendation, ...], Dict[Tuple[str, int], int]
]:
    starts_by_month = [0] * assembly.scenario.horizon_months
    plan: Dict[Tuple[str, int], int] = {}
    recommendations = []
    roles_by_key = {role.key: role for role in assembly.scenario.roles}
    for recommendation in optimization.recommendations:
        identity = assembly.role_identities_by_engine_key.get(recommendation.role_key)
        role = roles_by_key.get(recommendation.role_key)
        if identity is None or role is None:
            raise ProductionOptimizationFailure("Optimizer returned an unknown persisted role identity.")
        if (
            not isinstance(recommendation.hires, int)
            or recommendation.hires <= 0
            or recommendation.decision_month < 0
            or recommendation.decision_month >= assembly.scenario.horizon_months
            or recommendation.arrival_month != recommendation.decision_month + role.hiring_lead_time
            or recommendation.arrival_month >= assembly.scenario.horizon_months
        ):
            raise ProductionOptimizationFailure("Optimizer returned a hire outside the valid planning horizon.")
        expected_cost = (
            role.monthly_loaded_cost
            * (assembly.scenario.horizon_months - recommendation.arrival_month)
            * recommendation.hires
        )
        if abs(recommendation.incremental_cost - expected_cost) > PRIMARY_OBJECTIVE_TOLERANCE:
            raise ProductionOptimizationFailure("Optimizer returned an inconsistent incremental workforce cost.")
        if (recommendation.role_key, recommendation.decision_month) in plan:
            raise ProductionOptimizationFailure("Optimizer returned duplicate hiring-start recommendations.")
        starts_by_month[recommendation.decision_month] += recommendation.hires
        plan[(recommendation.role_key, recommendation.decision_month)] = recommendation.hires
        recommendations.append(
            ProductionHiringRecommendation(
                role_id=identity.role_id,
                department_id=identity.department_id,
                department=identity.department,
                role=identity.role,
                hires=recommendation.hires,
                decision_month=recommendation.decision_month + 1,
                arrival_month=recommendation.arrival_month + 1,
                planning_period_incremental_workforce_spend=recommendation.incremental_cost,
            )
        )
    if any(starts > capacity for starts, capacity in zip(starts_by_month, assembly.scenario.recruiting_capacity)):
        raise ProductionOptimizationFailure("Optimizer returned starts above submitted recruiting capacity.")
    return tuple(recommendations), plan


def _validate_optimization_result(
    assembly: ProductionOptimizationAssembly, baseline, optimization
) -> Tuple[Tuple[ProductionHiringRecommendation, ...], object]:
    if optimization.primary_status != "OPTIMAL" or optimization.secondary_status != "OPTIMAL":
        raise ProductionOptimizationFailure("Optimizer did not prove both lexicographic passes optimal.")
    recommendations, plan = _validated_recommendations(assembly, optimization)
    if optimization.budget_used > assembly.scenario.hiring_budget + PRIMARY_OBJECTIVE_TOLERANCE:
        raise ProductionOptimizationFailure("Optimizer returned spend above the submitted budget.")
    if (
        abs(
            optimization.budget_used
            - sum(item.planning_period_incremental_workforce_spend for item in recommendations)
        )
        > PRIMARY_OBJECTIVE_TOLERANCE
    ):
        raise ProductionOptimizationFailure("Optimizer returned inconsistent total workforce spend.")
    independently_recomputed = forecast_workforce(assembly.scenario, plan)
    if (
        independently_recomputed.total_understaffed_fte_months
        > optimization.primary_optimum + PRIMARY_OBJECTIVE_TOLERANCE
    ):
        raise ProductionOptimizationFailure(
            "Optimized forecast did not preserve the primary objective within tolerance."
        )
    if (
        independently_recomputed.total_understaffed_fte_months
        > baseline.total_understaffed_fte_months + PRIMARY_OBJECTIVE_TOLERANCE
    ):
        raise ProductionOptimizationFailure("Optimized understaffing is worse than the feasible zero-hire baseline.")
    return recommendations, independently_recomputed


def optimize_production_workforce(
    session: Session,
    planning_period_incremental_workforce_budget: float,
    monthly_recruiting_capacity: Sequence[int],
) -> ProductionOptimizationResult:
    """Run the fail-closed production optimization path using the authoritative M1 solver."""
    try:
        assembly = assemble_production_optimization_inputs(
            session,
            planning_period_incremental_workforce_budget,
            monthly_recruiting_capacity,
        )
        baseline = forecast_workforce(assembly.scenario)
    except InputValidationError as error:
        raise ProductionOptimizationInputError(str(error)) from error
    started = perf_counter()
    try:
        optimization = optimize_hiring_plan(assembly.scenario)
    except SolverFailure as error:
        raise ProductionOptimizationFailure(str(error)) from error
    optimization_duration_ms = (perf_counter() - started) * 1_000
    recommendations, optimized_forecast = _validate_optimization_result(
        assembly, baseline, optimization
    )
    baseline_role_months = _role_months(assembly, baseline)
    optimized_role_months = _role_months(assembly, optimized_forecast)
    baseline_department_months, baseline_organization_months = _aggregates(
        baseline_role_months, assembly.planning_months
    )
    optimized_department_months, optimized_organization_months = _aggregates(
        optimized_role_months, assembly.planning_months
    )
    optimized_total = optimized_forecast.total_understaffed_fte_months
    return ProductionOptimizationResult(
        generated_at=datetime.now(timezone.utc),
        model_version=MODEL_VERSION,
        observation_date=assembly.observation_date,
        planning_horizon_months=assembly.scenario.horizon_months,
        submitted_budget=assembly.scenario.hiring_budget,
        submitted_monthly_recruiting_capacity=assembly.scenario.recruiting_capacity,
        solver=optimization.solver_name,
        primary_status=optimization.primary_status,
        secondary_status=optimization.secondary_status,
        optimization_duration_ms=optimization_duration_ms,
        baseline_understaffed_fte_months=baseline.total_understaffed_fte_months,
        baseline_role_months=baseline_role_months,
        baseline_department_months=baseline_department_months,
        baseline_organization_months=baseline_organization_months,
        optimized_understaffed_fte_months=optimized_total,
        improvement_understaffed_fte_months=(
            baseline.total_understaffed_fte_months - optimized_total
        ),
        planning_period_incremental_workforce_spend_used=optimization.budget_used,
        unused_budget=max(assembly.scenario.hiring_budget - optimization.budget_used, 0.0),
        recommendations=recommendations,
        optimized_role_months=optimized_role_months,
        optimized_department_months=optimized_department_months,
        optimized_organization_months=optimized_organization_months,
    )
