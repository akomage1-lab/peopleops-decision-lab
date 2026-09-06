"""Minimal FastAPI application for the M2 walking skeleton."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from peopleops.models import InputValidationError
from peopleops.optimizer import SolverFailure

from .analytics import workforce_history, workforce_summary
from .database import get_session
from .forecast_service import ForecastInputError, production_baseline_forecast
from .models import ScenarioRecord
from .schemas import (
    DepartmentMetricResponse,
    DepartmentForecastMonthResponse,
    OptimizeRequest,
    OptimizeResponse,
    OrganizationForecastMonthResponse,
    ProductionForecastResponse,
    RoleForecastMonthResponse,
    RoleForecastProvenanceResponse,
    ScenarioResponse,
    WorkforceHistoryPointResponse,
    WorkforceSummaryResponse,
)
from .service import optimize_record


def create_app() -> FastAPI:
    """Create the deliberately small M2 HTTP surface."""
    app = FastAPI(title="PeopleOps Decision Lab", version="0.3.0")

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

    @app.get("/api/workforce/summary", response_model=WorkforceSummaryResponse)
    def get_workforce_summary(
        start_month: Optional[date] = None,
        end_month: Optional[date] = None,
        session: Session = Depends(get_session),
    ) -> WorkforceSummaryResponse:
        try:
            summary = workforce_summary(session, start_month, end_month)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        return WorkforceSummaryResponse(
            as_of_month=summary.as_of_month,
            historical_start_month=summary.historical_start_month,
            historical_end_month=summary.historical_end_month,
            current_total_fte=summary.current_total_fte,
            total_staffing_target=summary.total_staffing_target,
            total_staffing_gap=summary.total_staffing_gap,
            hires=summary.hires,
            exits=summary.exits,
            attrition_rate=summary.attrition_rate,
            average_hiring_lead_time_days=summary.average_hiring_lead_time_days,
            median_hiring_lead_time_days=summary.median_hiring_lead_time_days,
            departments=[DepartmentMetricResponse(**metric.__dict__) for metric in summary.departments],
        )

    @app.get("/api/workforce/history", response_model=list[WorkforceHistoryPointResponse])
    def get_workforce_history(session: Session = Depends(get_session)) -> list[WorkforceHistoryPointResponse]:
        return [WorkforceHistoryPointResponse(**point.__dict__) for point in workforce_history(session)]

    @app.get("/api/departments", response_model=list[DepartmentMetricResponse])
    def get_departments(session: Session = Depends(get_session)) -> list[DepartmentMetricResponse]:
        return [
            DepartmentMetricResponse(**metric.__dict__)
            for metric in workforce_summary(session).departments
        ]

    @app.get("/api/workforce/forecast", response_model=ProductionForecastResponse)
    def get_production_forecast(
        session: Session = Depends(get_session),
    ) -> ProductionForecastResponse:
        try:
            forecast = production_baseline_forecast(session)
        except ForecastInputError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return ProductionForecastResponse(
            generated_at=forecast.generated_at,
            model_version=forecast.model_version,
            planning_horizon_months=forecast.planning_horizon_months,
            observation_date=forecast.observation_date,
            role_provenance=[RoleForecastProvenanceResponse(**item.__dict__) for item in forecast.role_provenance],
            role_months=[RoleForecastMonthResponse(**item.__dict__) for item in forecast.role_months],
            department_months=[DepartmentForecastMonthResponse(**item.__dict__) for item in forecast.department_months],
            organization_months=[OrganizationForecastMonthResponse(**item.__dict__) for item in forecast.organization_months],
        )

    return app


app = create_app()
