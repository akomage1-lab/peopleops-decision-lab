"""M7 server-side composition of authoritative M3 history and M4 baseline forecast."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from .analytics import (
    HiringLeadTimeBreakdown,
    WorkforceTrendPoint,
    hiring_lead_time_breakdown,
    workforce_history,
    workforce_summary,
)
from .forecast_service import ForecastAggregateMonth, production_baseline_forecast


@dataclass(frozen=True)
class OverviewDepartmentRisk:
    department: str
    current_fte: float
    next_planning_target: float
    current_staffing_gap: float
    total_understaffed_fte_months: float
    end_of_horizon_shortage: float
    recent_attrition_rate: Optional[float]
    recent_exits: int
    recent_hires: int


@dataclass(frozen=True)
class WorkforceOverview:
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
    forecast_months: Sequence[ForecastAggregateMonth]
    historical_trend: Sequence[WorkforceTrendPoint]
    department_risks: Sequence[OverviewDepartmentRisk]
    slowest_filling_roles: Sequence[HiringLeadTimeBreakdown]


def production_workforce_overview(session: Session) -> WorkforceOverview:
    """Compose, but never recalculate, the existing M3/M4 metric definitions."""
    history = workforce_history(session)
    if not history:
        raise ValueError("Overview requires observed workforce history.")
    current = workforce_summary(session)
    recent_start = history[max(0, len(history) - 3)].month
    recent = workforce_summary(session, recent_start, history[-1].month)
    forecast = production_baseline_forecast(session)
    forecast_by_department = {}
    for row in forecast.department_months:
        forecast_by_department.setdefault(row.department, []).append(row)
    current_by_department = {item.department: item for item in current.departments}
    recent_by_department = {item.department: item for item in recent.departments}
    department_risks = []
    for department, current_metric in current_by_department.items():
        rows = forecast_by_department.get(department, [])
        recent_metric = recent_by_department.get(department)
        department_risks.append(OverviewDepartmentRisk(
            department=department,
            current_fte=current_metric.current_fte,
            next_planning_target=current_metric.staffing_target,
            current_staffing_gap=current_metric.staffing_gap,
            total_understaffed_fte_months=sum(row.staffing_shortage for row in rows),
            end_of_horizon_shortage=rows[-1].staffing_shortage if rows else 0.0,
            recent_attrition_rate=(recent_metric.attrition_rate if recent_metric else None),
            recent_exits=(recent_metric.exits if recent_metric else 0),
            recent_hires=(recent_metric.hires if recent_metric else 0),
        ))
    department_risks.sort(
        key=lambda item: (-item.total_understaffed_fte_months, item.department)
    )
    lead_times = hiring_lead_time_breakdown(session)
    return WorkforceOverview(
        generated_at=datetime.now(timezone.utc),
        observation_date=current.as_of_month,
        next_planning_month=forecast.organization_months[0].month,
        recent_historical_start_month=recent.historical_start_month,
        recent_historical_end_month=recent.historical_end_month,
        current_total_fte=current.current_total_fte,
        next_planning_target=current.total_staffing_target,
        current_staffing_gap=current.total_staffing_gap,
        six_month_understaffed_fte_months=forecast.total_understaffed_fte_months,
        recent_hires=recent.hires,
        recent_exits=recent.exits,
        recent_attrition_rate=recent.attrition_rate,
        organization_median_time_to_fill_days=current.median_hiring_lead_time_days,
        forecast_months=forecast.organization_months,
        historical_trend=history,
        department_risks=tuple(department_risks),
        slowest_filling_roles=tuple(lead_times[:5]),
    )
