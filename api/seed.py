"""Deterministically seed the sole M2 scenario after applying migrations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .app.database import SessionLocal
from .app.models import ScenarioRecord, ScenarioRoleRecord


SEED_SCENARIO_ID = 1


def seed_database(session: Session) -> ScenarioRecord:
    """Replace scenario 1 with the deterministic aggregate M1-demo-derived inputs."""
    scenario = session.scalar(
        select(ScenarioRecord).where(ScenarioRecord.id == SEED_SCENARIO_ID)
    )
    if scenario is None:
        scenario = ScenarioRecord(
            id=SEED_SCENARIO_ID,
            name="M2 Seeded Workforce Plan",
            planning_horizon_months=6,
            planning_period_incremental_workforce_budget=170_000.0,
            recruiting_capacity=[2, 2, 2, 2, 2, 2],
        )
        session.add(scenario)
        session.flush()
    else:
        scenario.name = "M2 Seeded Workforce Plan"
        scenario.planning_horizon_months = 6
        scenario.planning_period_incremental_workforce_budget = 170_000.0
        scenario.recruiting_capacity = [2, 2, 2, 2, 2, 2]
        scenario.roles.clear()
        session.flush()

    scenario.roles.extend(
        [
            ScenarioRoleRecord(
                department="Sales", role="Account Executive", current_fte=7.0,
                annual_attrition_rate=0.18, staffing_targets=[8.0] * 6,
                hiring_lead_time=0, monthly_loaded_cost=11_000.0, in_flight_hires={},
            ),
            ScenarioRoleRecord(
                department="Product", role="Data Analyst", current_fte=3.5,
                annual_attrition_rate=0.12, staffing_targets=[4.0, 4.0, 4.0, 4.5, 4.5, 4.5],
                hiring_lead_time=1, monthly_loaded_cost=13_000.0, in_flight_hires={},
            ),
            ScenarioRoleRecord(
                department="Customer Support", role="Support Specialist", current_fte=4.5,
                annual_attrition_rate=0.08, staffing_targets=[5.5] * 6,
                hiring_lead_time=2, monthly_loaded_cost=8_000.0, in_flight_hires={"2": 1},
            ),
        ]
    )
    session.commit()
    session.refresh(scenario)
    return scenario


def main() -> None:
    """Seed the configured database; Alembic must already have created its schema."""
    with SessionLocal() as session:
        scenario = seed_database(session)
        print(f"Seeded scenario {scenario.id}: {scenario.name}")


if __name__ == "__main__":
    main()
