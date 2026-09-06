"""M7 executive overview composition and API parity tests."""

from __future__ import annotations

from datetime import date

import pytest

from api.app.analytics import workforce_history, workforce_summary
from api.app.forecast_service import production_baseline_forecast
from api.app.models import DepartmentRecord, PlanningMonthlyAssumptionRecord, WorkforceMonthlyFactRecord, WorkforceRoleRecord
from api.app.overview_service import production_workforce_overview
from api.seed import HISTORICAL_MONTHS, PLANNING_MONTHS


def test_m7_overview_composes_authoritative_m3_and_m4_metrics(session_factory) -> None:
    with session_factory() as session:
        overview = production_workforce_overview(session)
        summary = workforce_summary(session)
        history = workforce_history(session)
        forecast = production_baseline_forecast(session)

    assert overview.observation_date == summary.as_of_month == date(2025, 12, 1)
    assert overview.current_total_fte == pytest.approx(summary.current_total_fte)
    assert overview.current_total_fte == pytest.approx(160.0)
    assert overview.next_planning_target == pytest.approx(summary.total_staffing_target)
    assert overview.next_planning_target == pytest.approx(170.5)
    assert overview.current_staffing_gap == pytest.approx(summary.total_staffing_gap)
    assert overview.current_staffing_gap == pytest.approx(10.5)
    assert overview.six_month_understaffed_fte_months == pytest.approx(forecast.total_understaffed_fte_months)
    assert tuple(overview.forecast_months) == tuple(forecast.organization_months)
    assert tuple(overview.historical_trend) == tuple(history)
    assert overview.recent_historical_start_month == date(2025, 10, 1)
    assert overview.recent_historical_end_month == date(2025, 12, 1)


def test_m7_overview_exposes_ranked_risk_and_historical_evidence(session_factory) -> None:
    with session_factory() as session:
        overview = production_workforce_overview(session)

    assert [item.department for item in overview.department_risks[:3]] == [
        "Sales", "Engineering", "Customer Support"
    ]
    assert all(
        left.total_understaffed_fte_months >= right.total_understaffed_fte_months
        for left, right in zip(overview.department_risks, overview.department_risks[1:])
    )
    support = next(item for item in overview.department_risks if item.department == "Customer Support")
    assert support.recent_exits == 5
    assert support.recent_attrition_rate == pytest.approx(5 / ((30 + 30 + 28) / 3))
    account_executive = overview.slowest_filling_roles[0]
    assert (account_executive.department, account_executive.role) == ("Sales", "Account Executive")
    assert account_executive.completed_cycles == 3
    assert account_executive.median_days == pytest.approx(105.0)


def test_m7_overview_api_matches_composed_authoritative_values(client, session_factory) -> None:
    with session_factory() as session:
        direct = production_workforce_overview(session)

    response = client.get("/api/workforce/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["observation_date"] == direct.observation_date.isoformat()
    assert body["current_total_fte"] == pytest.approx(direct.current_total_fte)
    assert body["six_month_understaffed_fte_months"] == pytest.approx(direct.six_month_understaffed_fte_months)
    assert body["forecast_months"][-1]["staffing_shortage"] == pytest.approx(direct.forecast_months[-1].staffing_shortage)
    assert body["department_risks"][0]["department"] == "Sales"
    assert body["slowest_filling_roles"][0]["completed_cycles"] == 3


def test_m7_overview_preserves_null_attrition_when_no_denominator_exists(session_factory) -> None:
    with session_factory() as session:
        department = DepartmentRecord(name="M7 Zero Denominator")
        role = WorkforceRoleRecord(
            name="M7 Zero Role", monthly_loaded_cost=0, annual_expected_attrition_rate=0.0, hiring_lead_time=0,
        )
        department.roles.append(role)
        session.add(department)
        session.flush()
        for month in HISTORICAL_MONTHS:
            session.add(WorkforceMonthlyFactRecord(role_id=role.id, month=month, observed_fte=0, hires=0, exits=0))
        for month in PLANNING_MONTHS:
            session.add(PlanningMonthlyAssumptionRecord(role_id=role.id, month=month, staffing_target=0, in_flight_hires=0))
        session.flush()
        overview = production_workforce_overview(session)
        zero_metric = next(item for item in overview.department_risks if item.department == department.name)
        assert zero_metric.recent_attrition_rate is None
        session.rollback()
