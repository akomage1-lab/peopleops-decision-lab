# PeopleOps Decision Lab — Workforce Planning & Optimization

PeopleOps Decision Lab is a small, aggregate workforce-planning proof of concept. Given department/role FTE, expected attrition, monthly targets, hiring lead times, in-flight arrivals, recruiting capacity, and a planning-period incremental workforce budget, it recommends hiring starts that minimize expected staffing shortages over six months.

M1 exists to kill-test the math and decision logic before any UI, database, workflow, or individual employee data is introduced. It is deliberately not an HR CRUD application.

## How the model works

The model plans at Department × Role × Month. It converts annual attrition `a` to an equivalent monthly rate with `1 - (1 - a) ** (1 / 12)`. Each month begins from the prior expected FTE after attrition, then adds in-flight arrivals and any optimized hires whose lead time has elapsed. Shortage is `max(target - expected_fte, 0)`, so expected FTE can remain fractional.

Hires are nonnegative integers by role and decision month. Starts whose arrival would land beyond the six-month horizon cannot be selected. The optimizer minimizes total understaffed FTE-months first, then runs a second, constrained solve to minimize in-horizon incremental hiring cost among equally good shortage outcomes. Costs cover only months after each optimized hire arrives. Monthly recruiting-start capacity and the planning-period incremental workforce budget are hard constraints.

## M1 install and checks

The project targets Python 3.9 or later. The local environment used for this M1 was Python 3.9.6. Create an isolated environment and install the minimal runtime plus test dependency:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

OR-Tools 9.10–9.11 is pinned because it supports the installed Python 3.9 environment and includes the linear solver interface used here.

## Run

```bash
.venv/bin/python -m pytest
.venv/bin/python -m peopleops.demo
```

The demo prints the six-month planning-period incremental workforce budget, baseline role shortages and aggregate understaffing, the recommended starts and arrivals, in-period workforce spend used, improvement, and both solver termination statuses.

## M2 walking skeleton

M2 adds one local end-to-end workflow: a seeded PostgreSQL scenario is read by FastAPI, adapted into the unchanged M1 engine, and displayed in a React/Vite page. The only editable browser input is the planning-period incremental workforce budget; overrides are used for that optimization request only and are not saved.

See [M2 walking-skeleton setup and run instructions](docs/M2_WALKING_SKELETON.md). Once PostgreSQL is running and migrated, start the API with `.venv/bin/uvicorn api.app.main:app --reload`, then run `npm run dev` in `web/` and open the shown local URL.

## M3 data and metrics foundation

M3 adds a deterministic, aggregate 12-month workforce history and six months of planning assumptions. Read-only APIs expose a workforce summary, historical trend, and department metrics; the M2 page deliberately remains unchanged. See [the M3 metric contract](docs/M3_METRICS.md) and [the synthetic demo-data story](docs/DEMO_DATA_STORY.md).

## M4 production forecast engine

M4 adapts persisted aggregate workforce observations and explicit future assumptions into the unchanged M1 baseline forecast engine. `GET /api/workforce/forecast` returns typed role-month forecasts, additive department and organization aggregates, and the provenance needed to explain them. See [the M4 production forecast contract](docs/M4_PRODUCTION_FORECAST.md).

## Limitations and assumptions

- The horizon is fixed to six months, and all inputs are synthetic aggregate expectations.
- Attrition is deterministic expected FTE, not employee-level stochastic simulation.
- New hires join fully at the end of a whole-month lead time; partial-month starts and productivity ramps are excluded.
- Costs are a simple loaded monthly cost charged from arrival through the end of M1. The planning-period incremental workforce budget therefore represents only optimized-hire workforce/payroll spend incurred inside the six-month horizon; existing and in-flight workforce costs are excluded.
- The model has one aggregate recruiting-capacity constraint per month. It does not yet model source channels, interviewer capacity, geographic constraints, or role-specific recruiting caps.
- A plan is only trusted if both solver passes terminate `OPTIMAL`; failures raise rather than return a guessed recommendation.

See [the frozen M0 contract](docs/PROJECT_CONTRACT.md) and [the M1 acceptance criteria](docs/M1_ACCEPTANCE.md) for the exact scope and test cases.
