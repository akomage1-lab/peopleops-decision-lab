"""Deterministic M3 aggregate-data, analytics, integrity, and API tests."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from api.app.analytics import hiring_lead_time, workforce_history, workforce_summary
from api.app.models import (
    CompletedHiringCycleRecord,
    DepartmentRecord,
    PlanningMonthlyAssumptionRecord,
    WorkforceMonthlyFactRecord,
    WorkforceRoleRecord,
)
from api.seed import DEMO_ROLE_SPECS, HISTORICAL_MONTHS


def test_m3_seed_has_documented_organization_size_and_current_total(session_factory) -> None:
    with session_factory() as session:
        departments = session.scalar(select(func.count()).select_from(DepartmentRecord))
        roles = session.scalar(select(func.count()).select_from(WorkforceRoleRecord))
        facts = session.scalar(select(func.count()).select_from(WorkforceMonthlyFactRecord))
        summary = workforce_summary(session)
    assert departments == 8
    assert roles == len(DEMO_ROLE_SPECS) == 19
    assert facts == 19 * 12
    assert summary.current_total_fte == pytest.approx(160.0)
    assert summary.total_staffing_target == pytest.approx(170.5)
    assert summary.total_staffing_gap == pytest.approx(10.5)


def test_m3_known_department_totals_and_deliberate_gap_patterns(session_factory) -> None:
    with session_factory() as session:
        summary = workforce_summary(session)
    metrics = {item.department: item for item in summary.departments}
    assert metrics["Engineering"].current_fte == pytest.approx(44.0)
    assert metrics["Sales"].current_fte == pytest.approx(39.0)
    assert metrics["Sales"].staffing_gap == pytest.approx(5.0)
    assert metrics["Security"].staffing_gap == pytest.approx(0.5)


def test_m3_known_hires_exits_and_highest_recent_attrition(session_factory) -> None:
    with session_factory() as session:
        recent = workforce_summary(session, date(2025, 10, 1), date(2025, 12, 1))
    metrics = {item.department: item for item in recent.departments}
    support = metrics["Customer Support"]
    assert support.exits == 5
    assert support.hires == 1
    assert support.attrition_rate == pytest.approx(5 / ((30 + 30 + 28) / 3))
    assert max(recent.departments, key=lambda item: item.attrition_rate or 0).department == "Customer Support"


def test_m3_hiring_lead_time_is_derived_from_completed_anonymous_cycles(session_factory) -> None:
    with session_factory() as session:
        account_executive = hiring_lead_time(session, "Sales", "Account Executive")
        no_cycles = hiring_lead_time(session, "Finance", "Accountant")
    assert account_executive.completed_cycles == 3
    assert account_executive.average_days == pytest.approx(105.0)
    assert account_executive.median_days == pytest.approx(105.0)
    assert no_cycles.completed_cycles == 0
    assert no_cycles.average_days is None
    assert no_cycles.median_days is None


def test_m3_workforce_history_is_complete_and_reproducible(session_factory) -> None:
    with session_factory() as session:
        history = workforce_history(session)
    assert len(history) == 12
    assert history[0].month == HISTORICAL_MONTHS[0]
    assert history[-1].month == HISTORICAL_MONTHS[-1]
    assert history[-1].total_fte == pytest.approx(160.0)
    assert history[-1].exits == 3


def test_m3_database_constraints_reject_negative_and_duplicate_monthly_facts(session_factory) -> None:
    with session_factory() as session:
        role = session.scalar(select(WorkforceRoleRecord).where(WorkforceRoleRecord.name == "Accountant"))
        assert role is not None
        session.add(WorkforceMonthlyFactRecord(role_id=role.id, month=date(2024, 1, 1), observed_fte=-1, hires=0, exits=0))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(WorkforceMonthlyFactRecord(role_id=role.id, month=date(2025, 1, 1), observed_fte=4, hires=0, exits=0))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(WorkforceMonthlyFactRecord(role_id=role.id, month=date(2024, 1, 2), observed_fte=4, hires=0, exits=0))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(PlanningMonthlyAssumptionRecord(role_id=role.id, month=date(2026, 7, 1), staffing_target=-1, in_flight_hires=0))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(CompletedHiringCycleRecord(role_id=role.id, opened_on=date(2025, 2, 1), started_on=date(2025, 1, 1)))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_m3_zero_fte_denominator_returns_no_attrition_rate(session_factory) -> None:
    with session_factory() as session:
        department = DepartmentRecord(name="Zero Denominator Test")
        role = WorkforceRoleRecord(name="Zero Role", monthly_loaded_cost=0)
        department.roles.append(role)
        session.add(department)
        session.flush()
        for month in HISTORICAL_MONTHS:
            session.add(WorkforceMonthlyFactRecord(role_id=role.id, month=month, observed_fte=0, hires=0, exits=0))
        session.add(PlanningMonthlyAssumptionRecord(role_id=role.id, month=date(2026, 1, 1), staffing_target=0, in_flight_hires=0))
        session.flush()
        metric = next(item for item in workforce_summary(session).departments if item.department == department.name)
        assert metric.attrition_rate is None
        session.rollback()


def test_m3_api_matches_authoritative_analytics_layer(client, session_factory) -> None:
    with session_factory() as session:
        direct = workforce_summary(session)
        direct_history = workforce_history(session)
    summary_response = client.get("/api/workforce/summary")
    history_response = client.get("/api/workforce/history")
    departments_response = client.get("/api/departments")
    assert summary_response.status_code == history_response.status_code == departments_response.status_code == 200
    summary = summary_response.json()
    assert summary["current_total_fte"] == pytest.approx(direct.current_total_fte)
    assert summary["total_staffing_gap"] == pytest.approx(direct.total_staffing_gap)
    assert len(history_response.json()) == len(direct_history) == 12
    assert history_response.json()[-1]["total_fte"] == pytest.approx(direct_history[-1].total_fte)
    assert {item["department"] for item in departments_response.json()} == {item.department for item in direct.departments}
