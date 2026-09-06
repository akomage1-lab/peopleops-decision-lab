# M4 Production Forecast Engine

## Data flow

The production baseline forecast is assembled as:

`workforce_monthly_facts + workforce_roles + planning_monthly_assumptions`
→ `forecast_service.assemble_forecast_inputs`
→ `peopleops.forecast.forecast_workforce`
→ typed service result and `GET /api/workforce/forecast`.

`analytics.py` remains limited to observed historical metrics. Future workforce
math is not duplicated in SQL, the API, or React: M1 is the authoritative
forecast engine.

## Starting-state and missing-data policy

The forecast uses the global latest observed fact month strictly before the
planning horizon as its observation date. Every persisted workforce role must
have a fact for that exact month.
Every role must also have the six consecutive planning-assumption months
starting at the earliest planning-assumption month. Missing a required fact or
assumption raises a clear `422` response; it is never interpreted as zero FTE
and no historical period is forward-filled.

The seeded demonstration therefore forecasts from the December 2025 observed
snapshot through January--June 2026.

## Persisted planning assumptions

`workforce_roles` holds role-level forward-looking assumptions:

- `annual_expected_attrition_rate` is the explicit future planning assumption.
- `hiring_lead_time` remains available for later planning/optimization use.
- `monthly_loaded_cost` remains the existing role cost input.

`planning_monthly_assumptions` holds the future monthly staffing target and
in-flight hires arriving in that month. `workforce_monthly_facts` remains the
separate record of observed historical FTE, hires, and exits. Historical
attrition is deliberately not substituted for the future attrition assumption.

## Forecast equation

For a role with annual expected attrition `a`, M1 converts it to:

`monthly_rate = 1 - (1 - a) ** (1 / 12)`

Each month applies the unchanged M1 recurrence:

`expected_fte[t] = expected_fte[t-1] * (1 - monthly_rate) + in_flight_hires[t]`

The baseline passes no optimizer-selected hires. Shortage is M1's
`max(staffing_target - expected_fte, 0)` and surplus is reported separately as
`max(expected_fte - staffing_target, 0)`.

## Output, aggregation, and provenance

The forecast API returns:

- role-month expected FTE before attrition, expected attrition loss, in-flight
  arrivals, expected FTE, target, shortage, and surplus;
- role provenance: department, role, observation date, starting observed FTE,
  annual expected attrition, targets, and in-flight arrivals;
- department-month and organization-month expected FTE, target, and shortage;
- generation time, observation date, six-month horizon, and model version
  `m1-baseline-forecast-v1`.

Department and organization values are sums of additive role quantities; gaps
are never averaged.

## Demonstration behavior

The deterministic seed has 19 roles across eight departments. Its first
forecast month (January 2026) has approximately 159.770 expected FTE against
a 170.5 target, a 10.730-FTE shortage. Customer Support's Support Specialist
role receives one in-flight January arrival, while Engineering and Sales have
growth-oriented targets and explicit attrition assumptions. Finance has a low,
stable 2% annual planning attrition assumption; Support and Sales use higher
future assumptions distinct from their observed historical rates.

## Limitations

M4 is a read-only baseline forecast. It does not persist forecast snapshots,
invent replacement hires, extend the planning horizon, or change the M1
optimizer/cost model. Forecast validity intentionally depends on complete,
explicit persisted observations and planning assumptions.
