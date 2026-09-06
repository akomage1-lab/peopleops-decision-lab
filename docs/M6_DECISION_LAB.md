# M6 Decision Lab

## Product workflow

The Decision Lab presents one compact workflow:

`Baseline → Scenario inputs → Run Scenario → Optimize Scenario → Compare`

The baseline is the persisted M4 production forecast. Scenario edits are sent
as explicit request payloads and remain transient. The optimizer then uses the
same transient assumptions through the M5/M1 production path.

## Scenario semantics

The UI allows edits to one selected Department × Role at a time:

- annual expected attrition;
- all six monthly staffing targets;
- organization-wide planning-period incremental workforce budget; and
- six organization-wide monthly recruiting-capacity values.

Starting FTE and in-flight hires always come from persisted M3/M4 data. Role
cost and lead time remain persisted M5 inputs. Reset clears transient role
overrides and restores the displayed role values from the production baseline;
it also restores the canonical demo decision constraints of $150,000 and two
starts per month.

## API flow

- `GET /api/workforce/forecast` returns the persisted baseline.
- `POST /api/workforce/scenario/forecast` applies explicit transient role
  overrides and runs the M1 forecast, with no optimizer-selected hires.
- `POST /api/workforce/scenario/optimize` applies those overrides plus the
  submitted budget/capacity and invokes the M5/M1 optimizer.

The services never write scenario values to PostgreSQL. Scenario requests are
validated for finite/nonnegative targets, attrition in `[0, 1)`, finite
nonnegative budget, six nonnegative integer capacities, valid role IDs, and
complete six-month target arrays.

## Three-way comparison

Baseline uses original persisted planning assumptions. Scenario shows the
no-new-hires consequence of the transient assumptions. Optimized Plan shows
the M1-recomputed outcome after the M5 recommendations. The comparison cards
show total understaffed FTE-months and Month 6 expected FTE, target, and
shortage; optimized additionally shows incremental spend.

The trajectory chart draws only API-returned expected FTE and target data. The
department table selects returned Month 6 department aggregates; React does not
independently calculate forecast or optimization metrics.

## Explainability boundary

The Decision Lab emits compact deterministic descriptions based on returned
recommendations and constraints. It states that V1 minimizes total
understaffed FTE-months and explicitly does not model role criticality, revenue
impact, skill scarcity, employee quality, candidate quality, or strategic
priority weights. No LLM, score, or arbitrary role weighting is used.

## Limitations

M6 adds no scenario persistence, dashboard, authentication, employee data,
advanced optimization constraints, or M7 executive analytics. The six-month,
aggregate M1/M5 model remains authoritative.
