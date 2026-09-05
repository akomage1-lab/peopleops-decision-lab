"""Two-pass OR-Tools MIP optimizer for aggregate hiring decisions."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Dict, List, Optional, Tuple

from ortools.linear_solver import pywraplp

from .forecast import annual_to_monthly_attrition, forecast_workforce
from .models import HireKey, HiringRecommendation, OptimizationResult, Scenario


# This is only a solver numerical-feasibility tolerance used when carrying the
# exact first-pass objective into pass two; it is not an objective weighting.
PRIMARY_OBJECTIVE_TOLERANCE = 1e-7


class SolverFailure(RuntimeError):
    """Raised when OR-Tools cannot prove the optimization result is optimal."""


@dataclass
class _ModelParts:
    solver: pywraplp.Solver
    solver_name: str
    hires: Dict[HireKey, pywraplp.Variable]
    shortages: List[pywraplp.Variable]
    cost_by_hire: Dict[HireKey, float]


def _make_solver() -> Tuple[pywraplp.Solver, str]:
    """Prefer SCIP, with an explicit CBC fallback only if SCIP is unavailable."""
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if solver is not None:
        return solver, "SCIP"
    solver = pywraplp.Solver.CreateSolver("CBC_MIXED_INTEGER_PROGRAMMING")
    if solver is not None:
        return solver, "CBC_MIXED_INTEGER_PROGRAMMING (SCIP unavailable)"
    raise SolverFailure("No supported OR-Tools mixed-integer solver is available (SCIP or CBC).")


def _status_name(status: int) -> str:
    names = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL",
        pywraplp.Solver.MODEL_INVALID: "MODEL_INVALID",
        pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
    }
    return names.get(status, f"UNKNOWN({status})")


def _build_model(scenario: Scenario, primary_cap: Optional[float] = None) -> _ModelParts:
    solver, solver_name = _make_solver()
    infinity = solver.infinity()
    hires: Dict[HireKey, pywraplp.Variable] = {}
    cost_by_hire: Dict[HireKey, float] = {}

    for role in scenario.roles:
        # A start at decision_month may exist only when it arrives in months 0..5.
        for decision_month in range(scenario.horizon_months - role.hiring_lead_time):
            key = (role.key, decision_month)
            hires[key] = solver.IntVar(
                0,
                scenario.recruiting_capacity[decision_month],
                f"hires_{len(hires)}",
            )
            arrival_month = decision_month + role.hiring_lead_time
            cost_by_hire[key] = role.monthly_loaded_cost * (
                scenario.horizon_months - arrival_month
            )

    for month, capacity in enumerate(scenario.recruiting_capacity):
        solver.Add(
            sum(variable for (role_key, decision_month), variable in hires.items() if decision_month == month)
            <= capacity
        )

    solver.Add(
        sum(cost_by_hire[key] * variable for key, variable in hires.items())
        <= scenario.hiring_budget
    )

    shortages: List[pywraplp.Variable] = []
    for role_index, role in enumerate(scenario.roles):
        monthly_attrition = annual_to_monthly_attrition(role.annual_attrition_rate)
        prior_expected: Optional[pywraplp.Variable] = None
        for month in range(scenario.horizon_months):
            expected = solver.NumVar(-infinity, infinity, f"expected_{role_index}_{month}")
            arriving = sum(
                variable
                for (role_key, decision_month), variable in hires.items()
                if role_key == role.key and decision_month + role.hiring_lead_time == month
            )
            in_flight = role.in_flight_hires.get(month, 0)
            if prior_expected is None:
                solver.Add(
                    expected == role.current_fte * (1 - monthly_attrition) + in_flight + arriving
                )
            else:
                solver.Add(expected == prior_expected * (1 - monthly_attrition) + in_flight + arriving)
            shortage = solver.NumVar(0, infinity, f"shortage_{role_index}_{month}")
            solver.Add(shortage >= role.staffing_targets[month] - expected)
            shortages.append(shortage)
            prior_expected = expected

    if primary_cap is not None:
        solver.Add(sum(shortages) <= primary_cap + PRIMARY_OBJECTIVE_TOLERANCE)
    return _ModelParts(
        solver=solver,
        solver_name=solver_name,
        hires=hires,
        shortages=shortages,
        cost_by_hire=cost_by_hire,
    )


def _require_optimal(status: int, pass_name: str) -> None:
    if status != pywraplp.Solver.OPTIMAL:
        raise SolverFailure(
            f"{pass_name} optimization did not prove an optimal solution: {_status_name(status)}."
        )


def optimize_hiring_plan(scenario: Scenario) -> OptimizationResult:
    """Minimize shortages first, then cost among equally optimal plans.

    This is a lexicographic two-pass mixed-integer program, rather than a
    weighted blend: pass one minimizes total understaffed FTE-months; pass two
    constrains that optimum and minimizes incremental in-horizon hiring cost.
    """
    primary = _build_model(scenario)
    solver_name = primary.solver_name
    primary_objective = primary.solver.Objective()
    for shortage in primary.shortages:
        primary_objective.SetCoefficient(shortage, 1.0)
    primary_objective.SetMinimization()
    primary_status_code = primary.solver.Solve()
    _require_optimal(primary_status_code, "Primary")
    primary_optimum = primary_objective.Value()
    if not isfinite(primary_optimum):
        raise SolverFailure("Primary optimization returned a non-finite objective value.")

    secondary = _build_model(scenario, primary_cap=primary_optimum)
    secondary_objective = secondary.solver.Objective()
    for key, variable in secondary.hires.items():
        secondary_objective.SetCoefficient(variable, secondary.cost_by_hire[key])
    secondary_objective.SetMinimization()
    secondary_status_code = secondary.solver.Solve()
    _require_optimal(secondary_status_code, "Secondary")

    plan: Dict[HireKey, int] = {}
    recommendations = []
    roles = {role.key: role for role in scenario.roles}
    for key, variable in secondary.hires.items():
        raw_quantity = variable.solution_value()
        quantity = int(round(raw_quantity))
        if abs(raw_quantity - quantity) > 1e-6:
            raise SolverFailure(f"Solver returned non-integral value {raw_quantity} for {key}.")
        if quantity:
            role_key, decision_month = key
            plan[key] = quantity
            arrival_month = decision_month + roles[role_key].hiring_lead_time
            recommendations.append(
                HiringRecommendation(
                    role_key=role_key,
                    decision_month=decision_month,
                    hires=quantity,
                    arrival_month=arrival_month,
                    incremental_cost=secondary.cost_by_hire[key] * quantity,
                )
            )

    forecast = forecast_workforce(scenario, plan)
    budget_used = sum(recommendation.incremental_cost for recommendation in recommendations)
    return OptimizationResult(
        solver_name=solver_name,
        primary_status=_status_name(primary_status_code),
        secondary_status=_status_name(secondary_status_code),
        recommendations=tuple(recommendations),
        forecast=forecast,
        budget_used=budget_used,
        primary_optimum=primary_optimum,
    )
