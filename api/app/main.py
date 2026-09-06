"""Minimal FastAPI application for the M2 walking skeleton."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
from datetime import date
from typing import AsyncIterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from peopleops.models import InputValidationError
from peopleops.optimizer import SolverFailure

from .analytics import workforce_history, workforce_summary
from .database import get_session
from .forecast_service import ForecastInputError, production_baseline_forecast
from .models import ScenarioRecord
from .optimization_service import (
    ProductionOptimizationFailure,
    ProductionOptimizationInputError,
    ProductionRoleOverride,
    forecast_production_scenario,
    optimize_production_workforce,
)
from .overview_service import production_workforce_overview
from .schemas import (
    DepartmentMetricResponse,
    DepartmentForecastMonthResponse,
    OptimizeRequest,
    OptimizeResponse,
    OrganizationForecastMonthResponse,
    ProductionHiringRecommendationResponse,
    ProductionForecastResponse,
    ProductionOptimizationDepartmentMonthResponse,
    ProductionOptimizationOrganizationMonthResponse,
    ProductionOptimizationRoleMonthResponse,
    ProductionOptimizeRequest,
    ProductionOptimizeResponse,
    ProductionScenarioForecastRequest,
    ProductionScenarioForecastResponse,
    ProductionScenarioOptimizeRequest,
    RoleForecastMonthResponse,
    RoleForecastProvenanceResponse,
    ScenarioResponse,
    WorkforceHistoryPointResponse,
    WorkforceOverviewResponse,
    WorkforceSummaryResponse,
    OverviewDepartmentRiskResponse,
    OverviewForecastMonthResponse,
    OverviewHistoricalTrendResponse,
    OverviewHiringLeadTimeResponse,
)
from .service import optimize_record


logger = logging.getLogger(__name__)
LOCAL_FRONTEND_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("PeopleOps Decision Lab API started")
    yield


def cors_origins_from_environment() -> tuple[str, ...]:
    """Return explicit CORS origins; production never falls back to a wildcard."""
    environment = os.getenv("APP_ENV", "development").strip().lower()
    configured = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )
    if environment == "production":
        if not configured:
            raise RuntimeError("ALLOWED_ORIGINS is required when APP_ENV=production.")
        return configured
    return configured or LOCAL_FRONTEND_ORIGINS


def create_app() -> FastAPI:
    """Create the compact aggregate workforce-planning HTTP surface."""
    app = FastAPI(
        title="PeopleOps Decision Lab", version="0.3.0", debug=False, lifespan=lifespan
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_origins_from_environment()),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        _request: Request, error: SQLAlchemyError
    ) -> JSONResponse:
        logger.error("Database request failed: %s", error.__class__.__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "The workforce data service is temporarily unavailable."},
        )

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
        except SolverFailure as error:
            logger.error("Seeded scenario optimization failed", exc_info=error)
            raise HTTPException(
                status_code=503,
                detail="The optimizer did not return a proven optimal plan.",
            )
        except InputValidationError as error:
            logger.error("Persisted seeded scenario is invalid", exc_info=error)
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
            logger.warning("Workforce summary request rejected: %s", error)
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

    @app.get("/api/workforce/overview", response_model=WorkforceOverviewResponse)
    def get_workforce_overview(
        session: Session = Depends(get_session),
    ) -> WorkforceOverviewResponse:
        try:
            overview = production_workforce_overview(session)
        except (ValueError, ForecastInputError) as error:
            logger.warning("Workforce overview request rejected: %s", error)
            raise HTTPException(status_code=422, detail=str(error))
        return WorkforceOverviewResponse(
            generated_at=overview.generated_at,
            observation_date=overview.observation_date,
            next_planning_month=overview.next_planning_month,
            recent_historical_start_month=overview.recent_historical_start_month,
            recent_historical_end_month=overview.recent_historical_end_month,
            current_total_fte=overview.current_total_fte,
            next_planning_target=overview.next_planning_target,
            current_staffing_gap=overview.current_staffing_gap,
            six_month_understaffed_fte_months=overview.six_month_understaffed_fte_months,
            recent_hires=overview.recent_hires,
            recent_exits=overview.recent_exits,
            recent_attrition_rate=overview.recent_attrition_rate,
            organization_median_time_to_fill_days=overview.organization_median_time_to_fill_days,
            forecast_months=[OverviewForecastMonthResponse(**item.__dict__) for item in overview.forecast_months],
            historical_trend=[OverviewHistoricalTrendResponse(**item.__dict__) for item in overview.historical_trend],
            department_risks=[OverviewDepartmentRiskResponse(**item.__dict__) for item in overview.department_risks],
            slowest_filling_roles=[OverviewHiringLeadTimeResponse(**item.__dict__) for item in overview.slowest_filling_roles],
        )

    @app.get("/api/workforce/forecast", response_model=ProductionForecastResponse)
    def get_production_forecast(
        session: Session = Depends(get_session),
    ) -> ProductionForecastResponse:
        try:
            forecast = production_baseline_forecast(session)
        except ForecastInputError as error:
            logger.warning("Production forecast request rejected: %s", error)
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
            total_understaffed_fte_months=forecast.total_understaffed_fte_months,
        )

    @app.post("/api/workforce/optimize", response_model=ProductionOptimizeResponse)
    def optimize_production_workforce_endpoint(
        request: ProductionOptimizeRequest,
        session: Session = Depends(get_session),
    ) -> ProductionOptimizeResponse:
        try:
            result = optimize_production_workforce(
                session,
                request.planning_period_incremental_workforce_budget,
                request.monthly_recruiting_capacity,
            )
        except ProductionOptimizationInputError as error:
            logger.warning("Production optimization request rejected: %s", error)
            raise HTTPException(status_code=422, detail=str(error))
        except ProductionOptimizationFailure as error:
            logger.error("Production optimization failed", exc_info=error)
            raise HTTPException(
                status_code=503,
                detail="The production optimizer did not return a proven optimal plan.",
            )
        return ProductionOptimizeResponse(
            generated_at=result.generated_at,
            model_version=result.model_version,
            observation_date=result.observation_date,
            planning_horizon_months=result.planning_horizon_months,
            submitted_budget=result.submitted_budget,
            submitted_monthly_recruiting_capacity=list(result.submitted_monthly_recruiting_capacity),
            solver=result.solver,
            primary_status=result.primary_status,
            secondary_status=result.secondary_status,
            optimization_duration_ms=result.optimization_duration_ms,
            baseline_understaffed_fte_months=result.baseline_understaffed_fte_months,
            baseline_role_months=[
                ProductionOptimizationRoleMonthResponse(**item.__dict__)
                for item in result.baseline_role_months
            ],
            baseline_department_months=[
                ProductionOptimizationDepartmentMonthResponse(**item.__dict__)
                for item in result.baseline_department_months
            ],
            baseline_organization_months=[
                ProductionOptimizationOrganizationMonthResponse(**item.__dict__)
                for item in result.baseline_organization_months
            ],
            optimized_understaffed_fte_months=result.optimized_understaffed_fte_months,
            improvement_understaffed_fte_months=result.improvement_understaffed_fte_months,
            planning_period_incremental_workforce_spend_used=(
                result.planning_period_incremental_workforce_spend_used
            ),
            unused_budget=result.unused_budget,
            recommendations=[
                ProductionHiringRecommendationResponse(**item.__dict__)
                for item in result.recommendations
            ],
            optimized_role_months=[
                ProductionOptimizationRoleMonthResponse(**item.__dict__)
                for item in result.optimized_role_months
            ],
            optimized_department_months=[
                ProductionOptimizationDepartmentMonthResponse(**item.__dict__)
                for item in result.optimized_department_months
            ],
            optimized_organization_months=[
                ProductionOptimizationOrganizationMonthResponse(**item.__dict__)
                for item in result.optimized_organization_months
            ],
        )

    @app.post("/api/workforce/scenario/forecast", response_model=ProductionScenarioForecastResponse)
    def forecast_transient_scenario(
        request: ProductionScenarioForecastRequest,
        session: Session = Depends(get_session),
    ) -> ProductionScenarioForecastResponse:
        overrides = tuple(
            ProductionRoleOverride(
                role_id=item.role_id,
                annual_expected_attrition_rate=item.annual_expected_attrition_rate,
                staffing_targets=(tuple(item.staffing_targets) if item.staffing_targets is not None else None),
            )
            for item in request.role_overrides
        )
        try:
            result = forecast_production_scenario(session, overrides)
        except ProductionOptimizationInputError as error:
            logger.warning("Transient scenario forecast request rejected: %s", error)
            raise HTTPException(status_code=422, detail=str(error))
        return ProductionScenarioForecastResponse(
            generated_at=result.generated_at,
            model_version=result.model_version,
            observation_date=result.observation_date,
            planning_horizon_months=result.planning_horizon_months,
            role_months=[
                ProductionOptimizationRoleMonthResponse(**item.__dict__)
                for item in result.role_months
            ],
            department_months=[
                ProductionOptimizationDepartmentMonthResponse(**item.__dict__)
                for item in result.department_months
            ],
            organization_months=[
                ProductionOptimizationOrganizationMonthResponse(**item.__dict__)
                for item in result.organization_months
            ],
            total_understaffed_fte_months=result.total_understaffed_fte_months,
        )

    @app.post("/api/workforce/scenario/optimize", response_model=ProductionOptimizeResponse)
    def optimize_transient_scenario(
        request: ProductionScenarioOptimizeRequest,
        session: Session = Depends(get_session),
    ) -> ProductionOptimizeResponse:
        overrides = tuple(
            ProductionRoleOverride(
                role_id=item.role_id,
                annual_expected_attrition_rate=item.annual_expected_attrition_rate,
                staffing_targets=(tuple(item.staffing_targets) if item.staffing_targets is not None else None),
            )
            for item in request.role_overrides
        )
        try:
            result = optimize_production_workforce(
                session,
                request.planning_period_incremental_workforce_budget,
                request.monthly_recruiting_capacity,
                overrides,
            )
        except ProductionOptimizationInputError as error:
            logger.warning("Transient scenario optimization request rejected: %s", error)
            raise HTTPException(status_code=422, detail=str(error))
        except ProductionOptimizationFailure as error:
            logger.error("Transient scenario optimization failed", exc_info=error)
            raise HTTPException(
                status_code=503,
                detail="The production optimizer did not return a proven optimal plan.",
            )
        return ProductionOptimizeResponse(
            generated_at=result.generated_at,
            model_version=result.model_version,
            observation_date=result.observation_date,
            planning_horizon_months=result.planning_horizon_months,
            submitted_budget=result.submitted_budget,
            submitted_monthly_recruiting_capacity=list(result.submitted_monthly_recruiting_capacity),
            solver=result.solver,
            primary_status=result.primary_status,
            secondary_status=result.secondary_status,
            optimization_duration_ms=result.optimization_duration_ms,
            baseline_understaffed_fte_months=result.baseline_understaffed_fte_months,
            baseline_role_months=[
                ProductionOptimizationRoleMonthResponse(**item.__dict__)
                for item in result.baseline_role_months
            ],
            baseline_department_months=[
                ProductionOptimizationDepartmentMonthResponse(**item.__dict__)
                for item in result.baseline_department_months
            ],
            baseline_organization_months=[
                ProductionOptimizationOrganizationMonthResponse(**item.__dict__)
                for item in result.baseline_organization_months
            ],
            optimized_understaffed_fte_months=result.optimized_understaffed_fte_months,
            improvement_understaffed_fte_months=result.improvement_understaffed_fte_months,
            planning_period_incremental_workforce_spend_used=(
                result.planning_period_incremental_workforce_spend_used
            ),
            unused_budget=result.unused_budget,
            recommendations=[
                ProductionHiringRecommendationResponse(**item.__dict__)
                for item in result.recommendations
            ],
            optimized_role_months=[
                ProductionOptimizationRoleMonthResponse(**item.__dict__)
                for item in result.optimized_role_months
            ],
            optimized_department_months=[
                ProductionOptimizationDepartmentMonthResponse(**item.__dict__)
                for item in result.optimized_department_months
            ],
            optimized_organization_months=[
                ProductionOptimizationOrganizationMonthResponse(**item.__dict__)
                for item in result.optimized_organization_months
            ],
        )

    return app


app = create_app()
