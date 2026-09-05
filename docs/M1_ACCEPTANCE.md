# M1 Acceptance Tests

All ten required golden cases are automated with deterministic pytest tests. The authoritative test implementation is in `tests/`.

| # | Golden case | Automated test | Acceptance assertion |
| --- | --- | --- | --- |
| 1 | No shortage | `test_1_no_shortage_requires_no_optimized_hires` | Zero starts and zero understaffed FTE-months. |
| 2 | Simple shortage, sufficient resources | `test_2_simple_shortage_hires_the_exact_needed_amount_without_overhiring` | Exactly two immediate hires; no shortage. |
| 3 | Zero planning-period incremental workforce budget | `test_3_zero_budget_leaves_shortage_and_recommends_no_hires` | No starts and the known shortage remains. |
| 4 | Lead time outside horizon | `test_4_lead_time_outside_horizon_has_no_meaningless_decisions` | No starts are representable; shortage remains. |
| 5 | Recruiting capacity | `test_5_recruiting_capacity_is_never_exceeded` | Every month remains at or below its capacity. |
| 6 | Limited-budget trade-off | `test_6_limited_budget_selects_allocation_with_lower_understaffing` | Funding the six-month Core need is selected over the lower-impact 0.5-FTE LateNeed. |
| 7 | Cost tie-breaker | `test_7_cost_tiebreaker_selects_lower_cost_plan_at_equal_minimum_shortage` | With one last-month recruiter slot, the cheaper equally effective role is selected. |
| 8 | Hiring lead-time effect | `test_8_longer_lead_time_cannot_improve_shortage_or_arrive_early` | Two-month lead produces two shortage months and no early FTE effect. |
| 9 | Attrition conversion / forecast | `test_9_attrition_conversion_and_manual_forecast` | Equivalent monthly rate and first three hand-calculated FTE values match. |
| 10 | Input validation | `test_10_input_validation_rejects_invalid_contract_values` | Negative FTE/target/budget/cost/lead/capacity, invalid attrition, and noninteger capacity are rejected. |

The separate `test_forecast_rejects_hire_arriving_beyond_horizon` is a direct guard for the no-meaningless-decision contract.

M1 passes only when this suite passes, the solver returns `OPTIMAL` for both passes, all constraints are represented in the model, and the demo remains within the documented aggregate scope.

## Final adversarial audit

The suite also checks that increasing the planning-period incremental workforce budget or recruiting capacity cannot worsen the optimum; increasing lead time cannot create pre-arrival coverage when budget is nonbinding; the optimized result is no worse than the feasible zero-hire baseline; every output arrival remains in months 0–5; spend and monthly starts remain within their constraints; and the recomputed second-pass shortage is at most the first-pass optimum plus `1e-7`.

The end-of-horizon case verifies that a lead-one start in Month 5 (zero-based decision month 4) arrives in Month 6, costs exactly one month of loaded cost, and is selected only because it removes a real Month-6 shortage. A lead-one start in Month 6 would arrive outside the horizon and is not representable.
