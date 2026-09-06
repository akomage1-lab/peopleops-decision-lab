"""M4 production-forecast adapter, parity, provenance, and API tests."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from api.app.analytics import workforce_summary
from api.app.forecast_service import (
    ForecastInputError,
    assemble_forecast_inputs,
    production_baseline_forecast,
)
from api.app.models import WorkforceMonthlyFactRecord, WorkforceRoleRecord
from peopleops.forecast import annual_to_monthly_attrition, forecast_workforce


def _role_month(forecast, department: str, role: str, month: date):
    return next(item for item in forecast.role_months if item.department == department and item.role == role and item.month == month)


def test_m4_starting_state_uses_latest_observed_fte(session_factory) -> None:
    with session_factory() as session:
        forecast = production_baseline_forecast(session)
    account_executive = next(item for item in forecast.role_provenance if item.department == "Sales" and item.role == "Account Executive")
    january = _role_month(forecast, "Sales", "Account Executive", date(2026, 1, 1))
    assert forecast.observation_date == date(2025, 12, 1)
    assert account_executive.starting_observed_fte == pytest.approx(22.0)
    assert january.expected_fte_before_attrition == pytest.approx(22.0)


def test_m4_starting_state_ignores_observations_inside_planning_horizon(session_factory) -> None:
    with session_factory() as session:
        role = session.scalar(select(WorkforceRoleRecord).where(WorkforceRoleRecord.name == "Accountant"))
        assert role is not None
        session.add(
            WorkforceMonthlyFactRecord(
                role_id=role.id, month=date(2026, 1, 1), observed_fte=99.0, hires=0, exits=0
            )
        )
        session.flush()
        forecast = production_baseline_forecast(session)
        assert forecast.observation_date == date(2025, 12, 1)
        assert _role_month(forecast, "Finance", "Accountant", date(2026, 1, 1)).expected_fte_before_attrition == pytest.approx(4.0)
        session.rollback()


def test_m4_missing_latest_observation_fails_without_treating_it_as_zero(session_factory) -> None:
    with session_factory() as session:
        role = session.scalar(select(WorkforceRoleRecord).where(WorkforceRoleRecord.name == "Accountant"))
        assert role is not None
        fact = session.scalar(select(WorkforceMonthlyFactRecord).where(WorkforceMonthlyFactRecord.role_id == role.id, WorkforceMonthlyFactRecord.month == date(2025, 12, 1)))
        assert fact is not None
        session.delete(fact)
        session.flush()
        with pytest.raises(ForecastInputError, match="Missing latest observed FTE"):
            production_baseline_forecast(session)
        session.rollback()


def test_m4_no_attrition_and_no_arrivals_remains_constant(session_factory) -> None:
    with session_factory() as session:
        role = session.scalar(select(WorkforceRoleRecord).where(WorkforceRoleRecord.name == "Accountant"))
        assert role is not None
        role.annual_expected_attrition_rate = 0.0
        for assumption in role.planning_assumptions:
            assumption.staffing_target = 4.0
            assumption.in_flight_hires = 0
        session.flush()
        forecast = production_baseline_forecast(session)
        rows = [item for item in forecast.role_months if item.department == "Finance" and item.role == "Accountant"]
        assert [item.expected_fte for item in rows] == pytest.approx([4.0] * 6)
        session.rollback()


def test_m4_attrition_only_matches_hand_calculated_m1_transition(session_factory) -> None:
    with session_factory() as session:
        role = session.scalar(select(WorkforceRoleRecord).where(WorkforceRoleRecord.name == "Accountant"))
        assert role is not None
        role.annual_expected_attrition_rate = 0.12
        for assumption in role.planning_assumptions:
            assumption.in_flight_hires = 0
        session.flush()
        forecast = production_baseline_forecast(session)
        january = _role_month(forecast, "Finance", "Accountant", date(2026, 1, 1))
        monthly_rate = annual_to_monthly_attrition(0.12)
        assert january.expected_attrition_loss == pytest.approx(4.0 * monthly_rate)
        assert january.expected_fte == pytest.approx(4.0 * (1 - monthly_rate))
        session.rollback()


def test_m4_inflight_arrival_and_gap_follow_m1_timing(session_factory) -> None:
    with session_factory() as session:
        forecast = production_baseline_forecast(session)
    january = _role_month(forecast, "Customer Support", "Support Specialist", date(2026, 1, 1))
    february = _role_month(forecast, "Customer Support", "Support Specialist", date(2026, 2, 1))
    rate = annual_to_monthly_attrition(0.12)
    assert january.in_flight_hires_arriving == 1
    assert january.expected_fte == pytest.approx(24.0 * (1 - rate) + 1)
    assert february.in_flight_hires_arriving == 0
    assert january.staffing_shortage == pytest.approx(26.0 - january.expected_fte)


def test_m4_department_and_organization_aggregations_are_additive(session_factory) -> None:
    with session_factory() as session:
        forecast = production_baseline_forecast(session)
    january = date(2026, 1, 1)
    engineering_roles = [item for item in forecast.role_months if item.department == "Engineering" and item.month == january]
    engineering = next(item for item in forecast.department_months if item.department == "Engineering" and item.month == january)
    organization = next(item for item in forecast.organization_months if item.month == january)
    assert engineering.expected_fte == pytest.approx(sum(item.expected_fte for item in engineering_roles))
    assert engineering.staffing_target == pytest.approx(sum(item.staffing_target for item in engineering_roles))
    assert organization.expected_fte == pytest.approx(sum(item.expected_fte for item in forecast.role_months if item.month == january))
    assert organization.staffing_shortage == pytest.approx(sum(item.staffing_shortage for item in forecast.role_months if item.month == january))


def test_m4_future_attrition_is_explicit_and_not_historical_attrition(session_factory) -> None:
    with session_factory() as session:
        forecast = production_baseline_forecast(session)
        recent_history = workforce_summary(session, date(2025, 10, 1), date(2025, 12, 1))
    support_provenance = next(item for item in forecast.role_provenance if item.department == "Customer Support" and item.role == "Support Specialist")
    support_history = next(item for item in recent_history.departments if item.department == "Customer Support")
    assert support_provenance.annual_expected_attrition_rate == pytest.approx(0.12)
    assert support_history.attrition_rate == pytest.approx(5 / ((30 + 30 + 28) / 3))
    assert support_history.attrition_rate != pytest.approx(support_provenance.annual_expected_attrition_rate)


def test_m4_production_adapter_matches_direct_m1_forecast(session_factory) -> None:
    with session_factory() as session:
        assembly = assemble_forecast_inputs(session)
        direct = forecast_workforce(assembly.scenario)
        production = production_baseline_forecast(session)
    for row in production.role_months:
        direct_row = direct.by_role[f"{row.department} / {row.role}"]
        index = assembly.planning_months.index(row.month)
        assert row.expected_fte == pytest.approx(direct_row.expected_fte[index])
        assert row.staffing_shortage == pytest.approx(direct_row.shortages[index])


def test_m4_api_matches_authoritative_production_forecast(client, session_factory) -> None:
    with session_factory() as session:
        direct = production_baseline_forecast(session)
    response = client.get("/api/workforce/forecast")
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == direct.model_version
    assert body["observation_date"] == direct.observation_date.isoformat()
    assert len(body["role_months"]) == len(direct.role_months) == 19 * 6
    assert body["organization_months"][0]["expected_fte"] == pytest.approx(direct.organization_months[0].expected_fte)
