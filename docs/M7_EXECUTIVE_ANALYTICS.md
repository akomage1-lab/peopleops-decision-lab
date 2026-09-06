# M7 Executive Workforce Analytics

## Product surface

M7 adds a concise **Overview** alongside the existing **Decision Lab**. The
Overview is the executive entry point: it makes current workforce position,
future staffing risk, recent observed attrition, and historical hiring speed
visible before a user chooses to model a constrained plan. The top navigation
is intentionally limited to these two connected surfaces.

The Overview links directly to Decision Lab. Decision Lab retains the M6
transient workflow and is the place to edit assumptions, submit the
planning-period incremental workforce budget and recruiting capacity, and run
the existing M1/M5 optimizer.

## Authoritative data contract

`GET /api/workforce/overview` is a server-side composition endpoint. It does
not introduce a new forecasting or optimization formula.

- Current observed FTE, next planning target, current gap, observed hiring,
  observed exits, observed attrition, and historical workforce trend come from
  the M3 analytics layer.
- Six-month organization trajectory and department cumulative/end-of-horizon
  shortages come from the persisted M4 baseline forecast.
- Hiring speed uses completed anonymous hiring-cycle durations from the M3
  analytics layer, grouped by department and role; the response includes both
  median days and completed-cycle count.

The browser renders returned metrics and rankings. It does not recompute
forecast totals, attrition, gap, risk ranking, or hiring lead-time measures.

## Questions answered

- **What is our current workforce position?** Current observed FTE, the next
  planning target, and current staffing gap identify the immediate position.
- **What happens over the next six months if nothing changes?** The baseline
  trajectory and total understaffed FTE-months use M4's persisted assumptions.
- **Where is future risk concentrated?** Departments are ranked by cumulative
  six-month baseline understaffed FTE-months, with Month 6 shortage shown as a
  complementary end-state indicator.
- **What has recently happened?** Recent hires, exits, and observed attrition
  use the clearly labeled last three available observed months.
- **Where has hiring taken longest?** The slowest completed cycles are ranked
  by historical median days and include their evidence count.

## Visual and temporal semantics

The **Six-month staffing trajectory** is explicitly a forward-looking baseline
forecast: expected FTE versus future staffing target. The **Observed workforce
trend** is explicitly historical FTE only. Labels distinguish observed dates,
the recent-history window, and the future planning month so no historical
actual is presented as forecast or vice versa.

All FTE values use one decimal where fractional expected FTE is meaningful.
Counts are whole numbers, percentage rates use one decimal percent, and
completed-cycle days use whole days. Missing rates or lead-time values render
as `Not available`; zero is never substituted for missing evidence.

## Scope boundary

M7 adds no new M1 math, changes no optimizer constraints, and adds no M8
features. It remains aggregate-only: no employee data, causal attrition claim,
people ranking, persistence workflow, authentication, or new optimization
objective is introduced.
