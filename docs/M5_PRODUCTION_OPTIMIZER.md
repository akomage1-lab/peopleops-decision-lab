# M5 Production Workforce Optimizer

## Data flow

The production optimization path is:

`workforce_monthly_facts + workforce_roles + planning_monthly_assumptions`
→ `assemble_production_optimization_inputs`
→ unchanged `peopleops.optimizer.optimize_hiring_plan`
→ independently validated typed result
→ `POST /api/workforce/optimize`.

The adapter begins with the M4 input assembler, so the production baseline and
optimizer consume the same persisted observation and planning assumptions. No
optimization formula exists in SQL, FastAPI formatting, or React.

## Inputs and constraints

Persisted inputs are the M4 starting observation, annual expected attrition,
monthly targets, in-flight arrivals, hiring lead time, and monthly loaded
cost. The request must explicitly include both:

- `planning_period_incremental_workforce_budget`
- `monthly_recruiting_capacity` (six nonnegative organization-wide values)

M1 uses nonnegative integer starts by role and decision month. A start is only
representable when its arrival is inside the six-month horizon. The primary
objective minimizes total understaffed FTE-months. The secondary pass minimizes
incremental spend subject to preserving that primary optimum within
`PRIMARY_OBJECTIVE_TOLERANCE = 1e-7` FTE-months.

## Budget and cost semantics

`workforce_roles.monthly_loaded_cost` is already a monthly loaded workforce
cost per FTE, exactly the unit consumed by M1; there is no conversion. A
recommended hire costs `monthly_loaded_cost * (6 - arrival_month_zero_based)`:
only months from arrival through the end of the planning period count. Existing
workforce and already in-flight hires do not consume this incremental budget.

## Stable identity and result model

The adapter aliases every M1 role with persisted department and workforce-role
primary keys, rather than using display titles as solver identity. Results map
back to `department_id`, department name, `role_id`, and role title. Roles with
the same display title in different departments therefore remain distinct.

The response provides request provenance, solver/status, total solve duration,
baseline and optimized role/month forecasts, additive department/organization
aggregates, totals, improvement, spend used/unused, and one-based start and
arrival months for each recommendation.

## Baseline parity and fail-closed behavior

Before solving, M5 obtains the zero-new-hire baseline through the same M1
forecast semantics as M4. Tests compare every role/month expected FTE, target,
and shortage, plus total understaffing.

M1 already requires both lexicographic passes to be `OPTIMAL`. M5 additionally
rebuilds the optimized hire plan, independently recomputes its forecast, checks
the primary tolerance, budget, monthly capacity, valid arrivals, and that the
feasible zero-hire baseline was not worsened. Any failure becomes a safe `503`
instead of a recommendation response. Invalid/missing request constraints are
rejected with `422`.

## Endpoint

`POST /api/workforce/optimize`

```json
{
  "planning_period_incremental_workforce_budget": 150000,
  "monthly_recruiting_capacity": [2, 2, 2, 2, 2, 2]
}
```

This is the M3/M4-backed production path intended for a future product UI.
`POST /api/scenarios/1/optimize` remains only as the M2 regression workflow.

## Seeded demo cases

With the deterministic 19-role seed, both cases have a baseline of
`117.610375669416` understaffed FTE-months and `[2, 2, 2, 2, 2, 2]` capacity.

- **Case A:** $150,000 budget; optimized understaffing `97.862896094968`,
  improvement `19.747479574448`, all $150,000 used, and seven starts. The
  solver allocates all starts to Sales Development Representative across Months
  1--5.
- **Case B:** $400,000 budget; optimized understaffing `87.998145235723`,
  improvement `29.612230433693`, $249,000 used, $151,000 unused, and ten
  starts. Allocations include Sales Development Representative (seven starts),
  plus one each for Support Specialist, QA Engineer, and Growth Marketer.

Both passes returned `OPTIMAL`. On ten local Case B runs, total M1 two-pass
solve time was 51.962--65.758 ms (52.686 ms median), which is comfortably
interactive for this 19-role demo. This is solver time only; it excludes HTTP
transport and response serialization.

## Limitations

M5 adds no role weights, priority scores, quotas, role-specific capacity,
headcount ceilings, scenario persistence, UI, or AI explanations. It remains a
transparent six-month aggregate model and relies on the complete explicit M4
data contract.
