"""Production M4 adapter from persisted aggregate data to the existing M1 forecast engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from peopleops.forecast import annual_to_monthly_attrition, forecast_workforce
from peopleops.models import RolePlan, Scenario

from .models import (
    DepartmentRecord,
    PlanningMonthlyAssumptionRecord,
    WorkforceMonthlyFactRecord,
    WorkforceRoleRecord,
)


MODEL_VERSION = "m1-baseline-forecast-v1"
PLANNING_HORIZON_MONTHS = 6


class ForecastInputError(ValueError):
    """Raised when persisted aggregate facts/assumptions cannot support a truthful forecast."""


@dataclass(frozen=True)
class RoleForecastProvenance:
    role_id: int
    department_id: int
    department: str
    role: str
    observation_date: date
    starting_observed_fte: float
    annual_expected_attrition_rate: float
    staffing_targets: Tuple[float, ...]
    in_flight_hires: Tuple[int, ...]


@dataclass(frozen=True)
class RoleForecastMonth:
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


@dataclass(frozen=True)
class ForecastAggregateMonth:
    month: date
    expected_fte: float
    staffing_target: float
    staffing_shortage: float


@dataclass(frozen=True)
class DepartmentForecastAggregateMonth(ForecastAggregateMonth):
    department: str


@dataclass(frozen=True)
class ProductionForecast:
    generated_at: datetime
    model_version: str
    planning_horizon_months: int
    observation_date: date
    role_provenance: Sequence[RoleForecastProvenance]
    role_months: Sequence[RoleForecastMonth]
    department_months: Sequence[DepartmentForecastAggregateMonth]
    organization_months: Sequence[ForecastAggregateMonth]
    total_understaffed_fte_months: float


@dataclass(frozen=True)
class ForecastAssembly:
    scenario: Scenario
    planning_months: Tuple[date, ...]
    provenance: Sequence[RoleForecastProvenance]
    observation_date: date


def _add_months(first_month: date, count: int) -> Tuple[date, ...]:
    return tuple(
        date(
            first_month.year + (first_month.month - 1 + offset) // 12,
            (first_month.month - 1 + offset) % 12 + 1,
            1,
        )
        for offset in range(count)
    )


def assemble_forecast_inputs(session: Session) -> ForecastAssembly:
    """Read complete M3 facts/assumptions and adapt them to an untouched M1 Scenario.

    Policy: all forecasted roles must have an observed snapshot in the global
    latest fact month before the planning horizon and six consecutive
    assumption rows from the first planning month. Missing data raises clearly;
    it is never treated as zero or forward-filled.
    """
    first_planning_month = session.scalar(select(func.min(PlanningMonthlyAssumptionRecord.month)))
    if first_planning_month is None:
        raise ForecastInputError("Forecast requires observed facts and planning assumptions.")
    observation_date = session.scalar(
        select(func.max(WorkforceMonthlyFactRecord.month)).where(
            WorkforceMonthlyFactRecord.month < first_planning_month
        )
    )
    if observation_date is None:
        raise ForecastInputError("Forecast requires observed facts before the planning horizon.")
    planning_months = _add_months(first_planning_month, PLANNING_HORIZON_MONTHS)
    roles = list(session.scalars(
        select(WorkforceRoleRecord)
        .join(WorkforceRoleRecord.department)
        .options(
            selectinload(WorkforceRoleRecord.department),
            selectinload(WorkforceRoleRecord.monthly_facts),
            selectinload(WorkforceRoleRecord.planning_assumptions),
        )
        .order_by(DepartmentRecord.name, WorkforceRoleRecord.name)
    ))
    if not roles:
        raise ForecastInputError("Forecast requires at least one workforce role.")
    missing_observations = []
    missing_assumptions = []
    m1_roles = []
    provenance = []
    for role in roles:
        fact = next((item for item in role.monthly_facts if item.month == observation_date), None)
        role_label = f"{role.department.name} / {role.name}"
        if fact is None:
            missing_observations.append(role_label)
            continue
        assumptions_by_month = {item.month: item for item in role.planning_assumptions}
        absent = [month.isoformat() for month in planning_months if month not in assumptions_by_month]
        if absent:
            missing_assumptions.append(f"{role_label}: {', '.join(absent)}")
            continue
        assumptions = tuple(assumptions_by_month[month] for month in planning_months)
        in_flight = tuple(item.in_flight_hires for item in assumptions)
        m1_roles.append(RolePlan(
            department=role.department.name,
            role=role.name,
            current_fte=fact.observed_fte,
            annual_attrition_rate=role.annual_expected_attrition_rate,
            staffing_targets=tuple(item.staffing_target for item in assumptions),
            hiring_lead_time=role.hiring_lead_time,
            monthly_loaded_cost=role.monthly_loaded_cost,
            in_flight_hires={index: hires for index, hires in enumerate(in_flight) if hires},
        ))
        provenance.append(RoleForecastProvenance(
            role_id=role.id,
            department_id=role.department_id,
            department=role.department.name,
            role=role.name,
            observation_date=observation_date,
            starting_observed_fte=fact.observed_fte,
            annual_expected_attrition_rate=role.annual_expected_attrition_rate,
            staffing_targets=tuple(item.staffing_target for item in assumptions),
            in_flight_hires=in_flight,
        ))
    if missing_observations:
        raise ForecastInputError("Missing latest observed FTE for: " + "; ".join(missing_observations))
    if missing_assumptions:
        raise ForecastInputError("Missing six-month planning assumptions for: " + "; ".join(missing_assumptions))
    return ForecastAssembly(
        scenario=Scenario(
            roles=tuple(m1_roles),
            hiring_budget=0.0,
            recruiting_capacity=(0,) * PLANNING_HORIZON_MONTHS,
        ),
        planning_months=planning_months,
        provenance=tuple(provenance),
        observation_date=observation_date,
    )


def production_baseline_forecast(session: Session) -> ProductionForecast:
    """Generate a no-new-hires baseline through the authoritative M1 forecast engine."""
    assembly = assemble_forecast_inputs(session)
    m1_result = forecast_workforce(assembly.scenario)
    role_months = []
    for role, provenance in zip(assembly.scenario.roles, assembly.provenance):
        result = m1_result.by_role[role.key]
        monthly_rate = annual_to_monthly_attrition(role.annual_attrition_rate)
        prior_expected = provenance.starting_observed_fte
        for index, month in enumerate(assembly.planning_months):
            attrition_loss = prior_expected * monthly_rate
            expected = result.expected_fte[index]
            target = role.staffing_targets[index]
            role_months.append(RoleForecastMonth(
                role_id=provenance.role_id,
                department_id=provenance.department_id,
                department=role.department,
                role=role.role,
                month=month,
                expected_fte_before_attrition=prior_expected,
                expected_attrition_loss=attrition_loss,
                in_flight_hires_arriving=provenance.in_flight_hires[index],
                expected_fte=expected,
                staffing_target=target,
                staffing_shortage=result.shortages[index],
                staffing_surplus=max(expected - target, 0.0),
            ))
            prior_expected = expected
    department_months = []
    organization_months = []
    for month in assembly.planning_months:
        month_rows = [item for item in role_months if item.month == month]
        for department in sorted({item.department for item in month_rows}):
            rows = [item for item in month_rows if item.department == department]
            department_months.append(DepartmentForecastAggregateMonth(
                department=department,
                month=month,
                expected_fte=sum(item.expected_fte for item in rows),
                staffing_target=sum(item.staffing_target for item in rows),
                staffing_shortage=sum(item.staffing_shortage for item in rows),
            ))
        organization_months.append(ForecastAggregateMonth(
            month=month,
            expected_fte=sum(item.expected_fte for item in month_rows),
            staffing_target=sum(item.staffing_target for item in month_rows),
            staffing_shortage=sum(item.staffing_shortage for item in month_rows),
        ))
    return ProductionForecast(
        generated_at=datetime.now(timezone.utc),
        model_version=MODEL_VERSION,
        planning_horizon_months=PLANNING_HORIZON_MONTHS,
        observation_date=assembly.observation_date,
        role_provenance=assembly.provenance,
        role_months=tuple(role_months),
        department_months=tuple(department_months),
        organization_months=tuple(organization_months),
        total_understaffed_fte_months=m1_result.total_understaffed_fte_months,
    )
