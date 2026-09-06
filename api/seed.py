"""Deterministically seed M2 plus the deliberate aggregate M3 demo organization."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Iterable, Tuple

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .app.database import SessionLocal
from .app.models import (
    CompletedHiringCycleRecord,
    DepartmentRecord,
    PlanningMonthlyAssumptionRecord,
    ScenarioRecord,
    ScenarioRoleRecord,
    WorkforceMonthlyFactRecord,
    WorkforceRoleRecord,
)


SEED_SCENARIO_ID = 1
HISTORICAL_MONTHS = tuple(date(2025, month, 1) for month in range(1, 13))
PLANNING_MONTHS = tuple(date(2026, month, 1) for month in range(1, 7))

# This is intentionally hand-authored rather than random data. Final FTE values
# sum to 160 and the event patterns underpin the documented demo story.
DEMO_ROLE_SPECS = (
    ("Engineering", "Software Engineer", 28.0, 16_000.0, {2: 1, 7: 1}, {10: 1}, (30, 30, 31, 31, 32, 32)),
    ("Engineering", "QA Engineer", 10.0, 12_000.0, {4: 1}, {}, (10, 10, 10, 11, 11, 11)),
    ("Engineering", "DevOps Engineer", 6.0, 17_000.0, {6: 1}, {}, (7, 7, 7, 7, 8, 8)),
    ("Sales", "Account Executive", 22.0, 11_000.0, {1: 1}, {8: 1}, (23, 23, 23, 24, 24, 24)),
    ("Sales", "Sales Development Representative", 14.0, 7_500.0, {3: 1}, {11: 1}, (18, 18, 19, 19, 20, 20)),
    ("Sales", "Sales Operations Analyst", 3.0, 10_000.0, {}, {}, (3, 3, 3, 3, 3, 3)),
    ("Customer Support", "Support Specialist", 24.0, 8_000.0, {2: 1, 10: 1}, {9: 2, 10: 1, 11: 2}, (26, 26, 27, 28, 30, 30)),
    ("Customer Support", "Support Team Lead", 4.0, 12_000.0, {}, {}, (4, 4, 4, 4, 4, 4)),
    ("Product", "Product Manager", 6.0, 15_000.0, {5: 1}, {}, (6, 6, 6, 6, 6, 6)),
    ("Product", "Data Analyst", 5.0, 13_000.0, {}, {}, (5, 5, 5, 5, 5, 5)),
    ("Product", "Product Designer", 4.0, 12_000.0, {}, {}, (4, 4, 4, 4, 4, 4)),
    ("Marketing", "Growth Marketer", 7.0, 10_000.0, {6: 1}, {}, (7, 7, 8, 8, 8, 8)),
    ("Marketing", "Content Marketer", 5.0, 8_500.0, {}, {}, (5, 5, 5, 5, 5, 5)),
    ("Finance", "Finance Analyst", 4.0, 11_000.0, {}, {}, (4, 4, 4, 4, 4, 4)),
    ("Finance", "Accountant", 4.0, 9_500.0, {}, {}, (4, 4, 4, 4, 4, 4)),
    ("Operations", "Operations Manager", 4.0, 12_000.0, {}, {}, (4, 4, 4, 4, 4, 4)),
    ("Operations", "People Ops Coordinator", 3.0, 8_000.0, {}, {}, (3, 3, 3, 3, 3, 3)),
    ("Security", "Security Engineer", 4.0, 21_000.0, {}, {}, (4.5, 4.5, 4.5, 4.5, 4.5, 4.5)),
    ("Security", "Compliance Analyst", 3.0, 10_500.0, {}, {}, (3, 3, 3, 3, 3, 3)),
)

FUTURE_ATTRITION_RATES = {
    "Engineering": 0.08, "Sales": 0.12, "Customer Support": 0.12,
    "Product": 0.06, "Marketing": 0.08, "Finance": 0.02,
    "Operations": 0.04, "Security": 0.03,
}
HIRING_LEAD_TIMES = {
    ("Sales", "Account Executive"): 3,
    ("Engineering", "Software Engineer"): 2,
    ("Engineering", "DevOps Engineer"): 2,
    ("Security", "Security Engineer"): 3,
}


def _seed_m2_scenario(session: Session) -> ScenarioRecord:
    scenario = session.scalar(select(ScenarioRecord).where(ScenarioRecord.id == SEED_SCENARIO_ID))
    if scenario is None:
        scenario = ScenarioRecord(id=SEED_SCENARIO_ID, name="M2 Seeded Workforce Plan", planning_horizon_months=6, planning_period_incremental_workforce_budget=170_000.0, recruiting_capacity=[2] * 6)
        session.add(scenario)
        session.flush()
    else:
        scenario.name = "M2 Seeded Workforce Plan"
        scenario.planning_horizon_months = 6
        scenario.planning_period_incremental_workforce_budget = 170_000.0
        scenario.recruiting_capacity = [2] * 6
        scenario.roles.clear()
        session.flush()
    scenario.roles.extend([
        ScenarioRoleRecord(department="Sales", role="Account Executive", current_fte=7.0, annual_attrition_rate=0.18, staffing_targets=[8.0] * 6, hiring_lead_time=0, monthly_loaded_cost=11_000.0, in_flight_hires={}),
        ScenarioRoleRecord(department="Product", role="Data Analyst", current_fte=3.5, annual_attrition_rate=0.12, staffing_targets=[4.0, 4.0, 4.0, 4.5, 4.5, 4.5], hiring_lead_time=1, monthly_loaded_cost=13_000.0, in_flight_hires={}),
        ScenarioRoleRecord(department="Customer Support", role="Support Specialist", current_fte=4.5, annual_attrition_rate=0.08, staffing_targets=[5.5] * 6, hiring_lead_time=2, monthly_loaded_cost=8_000.0, in_flight_hires={"2": 1}),
    ])
    return scenario


def _monthly_facts(final_fte: float, hires: Dict[int, int], exits: Dict[int, int]) -> Iterable[Tuple[float, int, int]]:
    fte = final_fte - sum(hires.values()) + sum(exits.values())
    for index in range(12):
        hired, exited = hires.get(index, 0), exits.get(index, 0)
        fte += hired - exited
        yield fte, hired, exited


def _seed_m3_organization(session: Session) -> None:
    session.execute(delete(DepartmentRecord))
    session.flush()
    departments: Dict[str, DepartmentRecord] = {}
    role_records: Dict[Tuple[str, str], WorkforceRoleRecord] = {}
    for department_name, role_name, _, cost, _, _, _ in DEMO_ROLE_SPECS:
        department = departments.get(department_name)
        if department is None:
            department = DepartmentRecord(name=department_name)
            session.add(department)
            session.flush()
            departments[department_name] = department
        role = WorkforceRoleRecord(
            name=role_name,
            monthly_loaded_cost=cost,
            annual_expected_attrition_rate=FUTURE_ATTRITION_RATES[department_name],
            hiring_lead_time=HIRING_LEAD_TIMES.get((department_name, role_name), 1),
        )
        department.roles.append(role)
        session.flush()
        role_records[(department_name, role_name)] = role

    for department_name, role_name, final_fte, _, hires, exits, targets in DEMO_ROLE_SPECS:
        role = role_records[(department_name, role_name)]
        for month, (fte, hired, exited) in zip(HISTORICAL_MONTHS, _monthly_facts(final_fte, hires, exits)):
            role.monthly_facts.append(WorkforceMonthlyFactRecord(month=month, observed_fte=fte, hires=hired, exits=exited))
        for month, target in zip(PLANNING_MONTHS, targets):
            role.planning_assumptions.append(PlanningMonthlyAssumptionRecord(month=month, staffing_target=float(target), in_flight_hires=1 if department_name == "Customer Support" and role_name == "Support Specialist" and month == PLANNING_MONTHS[0] else 0))

    cycle_specs = {
        ("Sales", "Account Executive"): ((date(2025, 3, 1), 90), (date(2025, 7, 1), 105), (date(2025, 11, 1), 120)),
        ("Engineering", "Software Engineer"): ((date(2025, 3, 1), 55), (date(2025, 8, 1), 60)),
        ("Customer Support", "Support Specialist"): ((date(2025, 3, 1), 35), (date(2025, 11, 1), 40)),
        ("Sales", "Sales Development Representative"): ((date(2025, 4, 1), 28),),
        ("Security", "Security Engineer"): ((date(2025, 9, 1), 75),),
    }
    for role_key, cycles in cycle_specs.items():
        for started_on, duration_days in cycles:
            role_records[role_key].completed_hiring_cycles.append(CompletedHiringCycleRecord(opened_on=started_on - timedelta(days=duration_days), started_on=started_on))


def seed_database(session: Session) -> ScenarioRecord:
    """Recreate the deterministic M2 scenario and M3 aggregate demo organization."""
    scenario = _seed_m2_scenario(session)
    _seed_m3_organization(session)
    session.commit()
    session.refresh(scenario)
    return scenario


def main() -> None:
    with SessionLocal() as session:
        scenario = seed_database(session)
        print(f"Seeded M2 scenario {scenario.id} and M3 aggregate organization ({len(DEMO_ROLE_SPECS)} roles).")


if __name__ == "__main__":
    main()
