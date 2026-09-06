# M3 Metric Contract

## Data boundaries

M3 stores three distinct kinds of aggregate data at Department × Role × Month:

- **Observed historical facts:** end-of-month FTE, hires, and exits in `workforce_monthly_facts`.
- **Planning assumptions:** future monthly staffing target, in-flight arrivals, and role loaded-cost assumption in `planning_monthly_assumptions` and `workforce_roles`.
- **Derived metrics:** values calculated at request time by `api/app/analytics.py`; they are never stored as facts.

M2 scenarios remain separate optimizer inputs. M3 does not alter M1 forecasting or optimization mathematics.

## Definitions

| Metric | Formula and units | Time/inclusion rules and edge cases |
| --- | --- | --- |
| Headcount / observed FTE | `observed_fte`; FTE, possibly fractional. | An end-of-month historical snapshot for one role. It excludes future assumptions. Negative values are rejected. |
| Expected FTE | Existing M1 expected workforce recurrence; FTE, possibly fractional. | Planning-only. It begins with prior expected FTE after attrition and adds in-flight and arrived optimized hires. It is not an M3 historical fact. |
| Staffing target | `staffing_target`; FTE. | Future planning assumption for one role/month. Negative values are rejected. Missing targets are not assumed to be zero. |
| Staffing gap | `max(staffing_target - current_observed_fte, 0)`; FTE. | M3 summary compares the latest observed historical month to the first future planning month. Surplus is reported as a zero gap, not a negative shortage. |
| Hires | `sum(hires)`; whole-person count. | Observed hires in all fact rows whose month is inclusively within the selected historical period. A zero is a recorded zero; missing rows are excluded rather than imputed. |
| Exits | `sum(exits)`; whole-person count. | Observed exits in all fact rows whose month is inclusively within the selected historical period. Negative values are rejected. |
| Historical attrition rate | `sum(exits) / average(monthly aggregate observed FTE)`; decimal rate. | The denominator is the arithmetic mean of each included end-of-month aggregate FTE total, not an industry benchmark. When its denominator is zero, return `null`; no rate is invented. Missing months are not imputed and therefore make a partial-period result explicitly dependent on available facts. |
| Hiring lead time / time-to-fill | `started_on - opened_on`; calendar days per anonymous completed hiring cycle. Average is arithmetic mean; median is conventional median of cycle durations. | Includes completed cycles matching the filter, irrespective of employee identity (none is stored). If no cycles exist, cycle count is 0 and average/median are `null`. A start before opening is rejected. |
| Planned incremental workforce spend | For M1 hire arriving in month `a`: `monthly_loaded_cost * (6 - a)`; currency. | Counts only optimized hire workforce/payroll spend incurred inside the six-month M1 horizon. Existing and in-flight workforce cost are excluded. |
| Understaffed FTE-months | `sum(role, month, max(target_fte - expected_fte, 0))`; FTE-months. | Existing M1 optimization objective over the planning horizon. A 2-FTE gap for three months contributes 6 FTE-months. |

## Summary endpoint boundaries

`GET /api/workforce/summary` defaults to the complete available historical period and reports the latest historical month as `as_of_month`. It aggregates current FTE from observed facts at that month and uses the earliest future planning-assumption month for targets/gaps. Optional `start_month` and `end_month` constrain hires, exits, and attrition inclusively; `start_month > end_month` is rejected.

Every metric is aggregate. There are no employee, candidate, demographic, payroll, or identity records in M3.
