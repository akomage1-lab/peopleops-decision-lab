"""Authoritative deterministic aggregate workforce metrics for M3."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .models import (
    CompletedHiringCycleRecord,
    DepartmentRecord,
    PlanningMonthlyAssumptionRecord,
    WorkforceMonthlyFactRecord,
    WorkforceRoleRecord,
)


@dataclass(frozen=True)
class DepartmentMetric:
    department: str
    current_fte: float
    staffing_target: float
    staffing_gap: float
    hires: int
    exits: int
    attrition_rate: Optional[float]


@dataclass(frozen=True)
class WorkforceSummary:
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
    departments: Sequence[DepartmentMetric]


@dataclass(frozen=True)
class WorkforceTrendPoint:
    month: date
    total_fte: float
    hires: int
    exits: int


@dataclass(frozen=True)
class HiringLeadTime:
    completed_cycles: int
    average_days: Optional[float]
    median_days: Optional[float]


@dataclass(frozen=True)
class HiringLeadTimeBreakdown:
    department: str
    role: str
    completed_cycles: int
    average_days: Optional[float]
    median_days: Optional[float]


def _facts(session: Session, start_month: date, end_month: date) -> List[WorkforceMonthlyFactRecord]:
    return list(session.scalars(
        select(WorkforceMonthlyFactRecord)
        .join(WorkforceMonthlyFactRecord.role)
        .options(joinedload(WorkforceMonthlyFactRecord.role).joinedload(WorkforceRoleRecord.department))
        .where(WorkforceMonthlyFactRecord.month.between(start_month, end_month))
        .order_by(WorkforceMonthlyFactRecord.month, WorkforceMonthlyFactRecord.id)
    ))


def hiring_lead_time(
    session: Session, department: Optional[str] = None, role: Optional[str] = None
) -> HiringLeadTime:
    """Average and median completed-cycle duration in calendar days, or None with no cycles."""
    query = select(CompletedHiringCycleRecord).join(CompletedHiringCycleRecord.role).join(WorkforceRoleRecord.department)
    if department is not None:
        query = query.where(DepartmentRecord.name == department)
    if role is not None:
        query = query.where(WorkforceRoleRecord.name == role)
    cycles = list(session.scalars(query))
    durations = [(cycle.started_on - cycle.opened_on).days for cycle in cycles]
    if not durations:
        return HiringLeadTime(0, None, None)
    return HiringLeadTime(len(durations), sum(durations) / len(durations), float(median(durations)))


def hiring_lead_time_breakdown(session: Session) -> Sequence[HiringLeadTimeBreakdown]:
    """Return historical completed-cycle lead-time evidence by aggregate role."""
    cycles = list(session.scalars(
        select(CompletedHiringCycleRecord)
        .join(CompletedHiringCycleRecord.role)
        .options(joinedload(CompletedHiringCycleRecord.role).joinedload(WorkforceRoleRecord.department))
    ))
    durations_by_role: Dict[tuple[str, str], List[int]] = {}
    for cycle in cycles:
        key = (cycle.role.department.name, cycle.role.name)
        durations_by_role.setdefault(key, []).append((cycle.started_on - cycle.opened_on).days)
    return tuple(sorted((
        HiringLeadTimeBreakdown(
            department=department,
            role=role,
            completed_cycles=len(durations),
            average_days=sum(durations) / len(durations),
            median_days=float(median(durations)),
        )
        for (department, role), durations in durations_by_role.items()
    ), key=lambda item: (-item.median_days if item.median_days is not None else 0, item.department, item.role)))


def workforce_summary(
    session: Session, start_month: Optional[date] = None, end_month: Optional[date] = None
) -> WorkforceSummary:
    """Compute M3 totals from observed facts and the first future planning month."""
    latest_month = session.scalar(select(func.max(WorkforceMonthlyFactRecord.month)))
    earliest_month = session.scalar(select(func.min(WorkforceMonthlyFactRecord.month)))
    if latest_month is None or earliest_month is None:
        raise ValueError("No observed workforce facts are available.")
    start = start_month or earliest_month
    end = end_month or latest_month
    if start > end:
        raise ValueError("start_month must not be after end_month.")
    facts = _facts(session, start, end)
    current_facts = [fact for fact in facts if fact.month == latest_month]
    planning_month = session.scalar(select(func.min(PlanningMonthlyAssumptionRecord.month)))
    assumptions = list(session.scalars(
        select(PlanningMonthlyAssumptionRecord)
        .join(PlanningMonthlyAssumptionRecord.role)
        .options(joinedload(PlanningMonthlyAssumptionRecord.role).joinedload(WorkforceRoleRecord.department))
        .where(PlanningMonthlyAssumptionRecord.month == planning_month)
    ))
    current_by_department: Dict[str, float] = {}
    for fact in current_facts:
        name = fact.role.department.name
        current_by_department[name] = current_by_department.get(name, 0.0) + fact.observed_fte
    target_by_department: Dict[str, float] = {}
    for assumption in assumptions:
        name = assumption.role.department.name
        target_by_department[name] = target_by_department.get(name, 0.0) + assumption.staffing_target

    facts_by_department: Dict[str, List[WorkforceMonthlyFactRecord]] = {}
    for fact in facts:
        facts_by_department.setdefault(fact.role.department.name, []).append(fact)
    department_metrics = []
    for department in sorted(set(current_by_department) | set(target_by_department)):
        department_facts = facts_by_department.get(department, [])
        exits = sum(fact.exits for fact in department_facts)
        hires = sum(fact.hires for fact in department_facts)
        monthly_totals: Dict[date, float] = {}
        for fact in department_facts:
            monthly_totals[fact.month] = monthly_totals.get(fact.month, 0.0) + fact.observed_fte
        average_monthly_fte = sum(monthly_totals.values()) / len(monthly_totals) if monthly_totals else 0.0
        department_metrics.append(DepartmentMetric(
            department=department,
            current_fte=current_by_department.get(department, 0.0),
            staffing_target=target_by_department.get(department, 0.0),
            staffing_gap=max(target_by_department.get(department, 0.0) - current_by_department.get(department, 0.0), 0.0),
            hires=hires,
            exits=exits,
            attrition_rate=exits / average_monthly_fte if average_monthly_fte else None,
        ))
    total_monthly_fte: Dict[date, float] = {}
    for fact in facts:
        total_monthly_fte[fact.month] = total_monthly_fte.get(fact.month, 0.0) + fact.observed_fte
    total_exits = sum(fact.exits for fact in facts)
    average_total_fte = sum(total_monthly_fte.values()) / len(total_monthly_fte) if total_monthly_fte else 0.0
    lead_time = hiring_lead_time(session)
    return WorkforceSummary(
        as_of_month=latest_month,
        historical_start_month=start,
        historical_end_month=end,
        current_total_fte=sum(current_by_department.values()),
        total_staffing_target=sum(target_by_department.values()),
        total_staffing_gap=sum(metric.staffing_gap for metric in department_metrics),
        hires=sum(fact.hires for fact in facts),
        exits=total_exits,
        attrition_rate=total_exits / average_total_fte if average_total_fte else None,
        average_hiring_lead_time_days=lead_time.average_days,
        median_hiring_lead_time_days=lead_time.median_days,
        departments=tuple(department_metrics),
    )


def workforce_history(session: Session) -> Sequence[WorkforceTrendPoint]:
    """Return the observed organization-level monthly trend without forecasting."""
    start = session.scalar(select(func.min(WorkforceMonthlyFactRecord.month)))
    end = session.scalar(select(func.max(WorkforceMonthlyFactRecord.month)))
    if start is None or end is None:
        return ()
    facts = _facts(session, start, end)
    grouped: Dict[date, List[WorkforceMonthlyFactRecord]] = {}
    for fact in facts:
        grouped.setdefault(fact.month, []).append(fact)
    return tuple(WorkforceTrendPoint(
        month=month,
        total_fte=sum(fact.observed_fte for fact in monthly_facts),
        hires=sum(fact.hires for fact in monthly_facts),
        exits=sum(fact.exits for fact in monthly_facts),
    ) for month, monthly_facts in sorted(grouped.items()))
