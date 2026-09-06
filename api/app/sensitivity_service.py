"""Bounded local constraint sensitivity using the authoritative production optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Sequence, Tuple

from sqlalchemy.orm import Session

from peopleops.optimizer import PRIMARY_OBJECTIVE_TOLERANCE

from .optimization_service import (
    MODEL_VERSION,
    ProductionOptimizationFailure,
    ProductionOptimizationResult,
    ProductionRoleOverride,
    optimize_production_workforce,
)


SENSITIVITY_MODEL_VERSION = f"{MODEL_VERSION}-m11-sensitivity-v1"
BUDGET_MULTIPLIERS = (0.5, 0.75, 1.0, 1.25, 1.5)
CAPACITY_DELTAS = (-1, 0, 1)


@dataclass(frozen=True)
class BudgetSensitivityPoint:
    budget: float
    optimized_understaffed_fte_months: float
    planning_period_incremental_workforce_spend_used: float
    unused_budget: float
    total_optimizer_selected_hires: int
    primary_status: str
    secondary_status: str
    optimization_duration_ms: float


@dataclass(frozen=True)
class RecruitingCapacitySensitivityPoint:
    monthly_recruiting_capacity: Tuple[int, ...]
    monthly_recruiting_capacity_delta: Tuple[int, ...]
    optimized_understaffed_fte_months: float
    planning_period_incremental_workforce_spend_used: float
    total_optimizer_selected_hires: int
    primary_status: str
    secondary_status: str
    optimization_duration_ms: float


@dataclass(frozen=True)
class ProductionConstraintSensitivityResult:
    generated_at: datetime
    model_version: str
    submitted_budget: float
    submitted_monthly_recruiting_capacity: Tuple[int, ...]
    budget_sensitivity: Tuple[BudgetSensitivityPoint, ...]
    recruiting_capacity_sensitivity: Tuple[RecruitingCapacitySensitivityPoint, ...]
    sensitivity_execution_duration_ms: float


def _total_hires(result: ProductionOptimizationResult) -> int:
    return sum(recommendation.hires for recommendation in result.recommendations)


def _budget_point(result: ProductionOptimizationResult) -> BudgetSensitivityPoint:
    return BudgetSensitivityPoint(
        budget=result.submitted_budget,
        optimized_understaffed_fte_months=result.optimized_understaffed_fte_months,
        planning_period_incremental_workforce_spend_used=result.planning_period_incremental_workforce_spend_used,
        unused_budget=result.unused_budget,
        total_optimizer_selected_hires=_total_hires(result),
        primary_status=result.primary_status,
        secondary_status=result.secondary_status,
        optimization_duration_ms=result.optimization_duration_ms,
    )


def _capacity_point(
    result: ProductionOptimizationResult, submitted_capacity: Tuple[int, ...]
) -> RecruitingCapacitySensitivityPoint:
    capacity = result.submitted_monthly_recruiting_capacity
    return RecruitingCapacitySensitivityPoint(
        monthly_recruiting_capacity=capacity,
        monthly_recruiting_capacity_delta=tuple(
            tested - submitted for tested, submitted in zip(capacity, submitted_capacity)
        ),
        optimized_understaffed_fte_months=result.optimized_understaffed_fte_months,
        planning_period_incremental_workforce_spend_used=result.planning_period_incremental_workforce_spend_used,
        total_optimizer_selected_hires=_total_hires(result),
        primary_status=result.primary_status,
        secondary_status=result.secondary_status,
        optimization_duration_ms=result.optimization_duration_ms,
    )


def _assert_nondecreasing_resources_do_not_worsen(points: Sequence[object]) -> None:
    values = [point.optimized_understaffed_fte_months for point in points]
    if any(later > earlier + PRIMARY_OBJECTIVE_TOLERANCE for earlier, later in zip(values, values[1:])):
        raise ProductionOptimizationFailure(
            "Sensitivity optimization violated the required resource monotonicity invariant."
        )


def analyze_constraint_sensitivity(
    session: Session,
    planning_period_incremental_workforce_budget: float,
    monthly_recruiting_capacity: Sequence[int],
    role_overrides: Sequence[ProductionRoleOverride] = (),
) -> ProductionConstraintSensitivityResult:
    """Rerun the proven optimizer at small deterministic local constraint variations."""
    submitted_capacity = tuple(monthly_recruiting_capacity)
    started = perf_counter()
    budgets = tuple(sorted({max(0.0, planning_period_incremental_workforce_budget * multiplier) for multiplier in BUDGET_MULTIPLIERS}))
    budget_points = tuple(
        _budget_point(
            optimize_production_workforce(session, budget, submitted_capacity, role_overrides)
        )
        for budget in budgets
    )
    _assert_nondecreasing_resources_do_not_worsen(budget_points)

    capacity_vectors = []
    for delta in CAPACITY_DELTAS:
        tested = tuple(max(0, value + delta) for value in submitted_capacity)
        if tested not in capacity_vectors:
            capacity_vectors.append(tested)
    capacity_points = tuple(
        _capacity_point(
            optimize_production_workforce(
                session,
                planning_period_incremental_workforce_budget,
                capacity,
                role_overrides,
            ),
            submitted_capacity,
        )
        for capacity in capacity_vectors
    )
    _assert_nondecreasing_resources_do_not_worsen(capacity_points)
    return ProductionConstraintSensitivityResult(
        generated_at=datetime.now(timezone.utc),
        model_version=SENSITIVITY_MODEL_VERSION,
        submitted_budget=planning_period_incremental_workforce_budget,
        submitted_monthly_recruiting_capacity=submitted_capacity,
        budget_sensitivity=budget_points,
        recruiting_capacity_sensitivity=capacity_points,
        sensitivity_execution_duration_ms=(perf_counter() - started) * 1_000,
    )
