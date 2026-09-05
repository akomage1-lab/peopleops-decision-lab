"""Minimal FastAPI application for the M2 walking skeleton."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from peopleops.models import InputValidationError
from peopleops.optimizer import SolverFailure

from .database import get_session
from .models import ScenarioRecord
from .schemas import OptimizeRequest, OptimizeResponse, ScenarioResponse
from .service import optimize_record


def create_app() -> FastAPI:
    """Create the deliberately small M2 HTTP surface."""
    app = FastAPI(title="PeopleOps Decision Lab", version="0.2.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    def scenario_or_404(scenario_id: int, session: Session) -> ScenarioRecord:
        scenario = session.scalar(
            select(ScenarioRecord)
            .options(selectinload(ScenarioRecord.roles))
            .where(ScenarioRecord.id == scenario_id)
        )
        if scenario is None:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        return scenario

    @app.get("/api/scenarios/{scenario_id}", response_model=ScenarioResponse)
    def get_scenario(scenario_id: int, session: Session = Depends(get_session)) -> ScenarioRecord:
        return scenario_or_404(scenario_id, session)

    @app.post("/api/scenarios/{scenario_id}/optimize", response_model=OptimizeResponse)
    def optimize_scenario(
        scenario_id: int,
        request: OptimizeRequest,
        session: Session = Depends(get_session),
    ) -> OptimizeResponse:
        scenario = scenario_or_404(scenario_id, session)
        try:
            return optimize_record(
                scenario, request.planning_period_incremental_workforce_budget
            )
        except SolverFailure:
            raise HTTPException(
                status_code=503,
                detail="The optimizer did not return a proven optimal plan.",
            )
        except InputValidationError:
            raise HTTPException(status_code=500, detail="Persisted scenario data is invalid.")

    return app


app = create_app()
