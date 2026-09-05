# PeopleOps Decision Lab — M0 Project Contract

## Purpose and scope

M1 is a six-month mathematical proof of concept for an aggregate workforce decision: given current workforce, expected attrition, staffing targets, lead times, in-flight hires, recruiting capacity, and a planning-period incremental workforce budget, recommend hiring starts that reduce expected staffing shortages. It is not a people-management system and does not make individual-level recommendations.

## Frozen planning inputs

The planning grain is **Department × Role × Month**. M1 fixes the horizon at six months.

Each department/role provides current FTE, annual expected attrition rate, six monthly staffing targets, an integer hiring lead time in months, loaded monthly cost for a new hire, and nonnegative whole in-flight hires indexed by their in-horizon arrival month. A scenario provides a nonnegative planning-period incremental workforce budget and a nonnegative whole recruiting-start capacity for each of the six months.

Inputs must be finite and nonnegative where applicable. Annual attrition is validated as `0 <= a < 1`; role lead times are nonnegative integers; targets, costs, FTE, and the planning-period incremental workforce budget cannot be negative. M1 rejects in-flight arrivals outside the horizon.

## Forecast contract

Annual attrition `a` is converted once per role:

`monthly_rate = 1 - (1 - a) ** (1 / 12)`

For role `r` and month `m`, with expected FTE `E`:

`E[r, m] = E[r, m-1] * (1 - monthly_rate[r]) + in_flight[r, m] + arrivals_from_optimized_starts[r, m]`

For month zero, `E[r, -1]` means current FTE. Attrition applies to the prior expected workforce; hires arriving that month are added afterwards. Expected FTE may be fractional because it is an expectation, not a partial person.

`shortage[r, m] = max(target_fte[r, m] - E[r, m], 0)`

## Optimization contract

The decision variable is `hires[r, d]`, a nonnegative integer number of starts for a department/role in decision month `d`. Its arrival is `d + lead_time[r]`. No variable is created if that arrival lies outside months 0–5; this makes meaningless decisions impossible.

The primary objective is to minimize total understaffed FTE-months:

`minimize sum(shortage[r, m])`

The secondary objective is transparent and lexicographic: after OR-Tools proves the primary optimum, a separate model constrains total shortage to that optimum (plus a documented `1e-7` solver floating-point tolerance) and minimizes incremental cost. There is no blended or opaque score.

For a hire arriving in month `a`, incremental cost is:

`monthly_loaded_cost[r] * (6 - a)`

This charges only the months the optimized hire is expected to have joined inside M1. Thus, the planning-period incremental workforce budget represents incremental workforce/payroll spend occurring inside the six-month horizon. It excludes both existing workforce cost and in-flight-hire cost.

Constraints are: total incremental cost does not exceed the planning-period incremental workforce budget; starts are whole people; every role lead time is respected; starts in any decision month do not exceed scenario recruiting capacity; and only arrivals inside the horizon are representable. After the second pass, the recomputed forecast total is checked against the first-pass optimum plus the same documented tolerance.

## Solver contract

The implementation uses Python OR-Tools `linear_solver` with SCIP when it is installed. It explicitly falls back to CBC only when SCIP is unavailable and reports that fact. Both optimization passes must report `OPTIMAL`; any other termination status raises an error instead of fabricating a recommendation.

## Explicit non-goals

M1 contains no individual employee data or profiles, applicant tracking, candidate ranking, payroll, PTO, performance data, firing/promotion recommendations, AI/LLM decision-making, UI, API, database, authentication, Docker, microservices, or M2 work.
