# PeopleOps Decision Lab — Workforce Planning & Optimization

PeopleOps Decision Lab is a small, aggregate workforce-planning proof of concept. Given department/role FTE, expected attrition, monthly targets, hiring lead times, in-flight arrivals, recruiting capacity, and a hiring budget, it recommends hiring starts that minimize expected staffing shortages over six months.

M1 exists to kill-test the math and decision logic before any UI, database, workflow, or individual employee data is introduced. It is deliberately not an HR CRUD application.

## How the model works

The model plans at Department × Role × Month. It converts annual attrition `a` to an equivalent monthly rate with `1 - (1 - a) ** (1 / 12)`. Each month begins from the prior expected FTE after attrition, then adds in-flight arrivals and any optimized hires whose lead time has elapsed. Shortage is `max(target - expected_fte, 0)`, so expected FTE can remain fractional.

Hires are nonnegative integers by role and decision month. Starts whose arrival would land beyond the six-month horizon cannot be selected. The optimizer minimizes total understaffed FTE-months first, then runs a second, constrained solve to minimize in-horizon incremental hiring cost among equally good shortage outcomes. Costs cover only months after each optimized hire arrives. Monthly recruiting-start capacity and total incremental budget are hard constraints.

## Install

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

The demo prints the six-month budget, baseline role shortages and aggregate understaffing, the recommended starts and arrivals, cost used, improvement, and both solver termination statuses.

## Limitations and assumptions

- The horizon is fixed to six months, and all inputs are synthetic aggregate expectations.
- Attrition is deterministic expected FTE, not employee-level stochastic simulation.
- New hires join fully at the end of a whole-month lead time; partial-month starts and productivity ramps are excluded.
- Costs are a simple loaded monthly cost charged from arrival through the end of M1. Existing and in-flight workforce costs are excluded from the incremental budget.
- The model has one aggregate recruiting-capacity constraint per month. It does not yet model source channels, interviewer capacity, geographic constraints, or role-specific recruiting caps.
- A plan is only trusted if both solver passes terminate `OPTIMAL`; failures raise rather than return a guessed recommendation.

See [the frozen M0 contract](docs/PROJECT_CONTRACT.md) and [the M1 acceptance criteria](docs/M1_ACCEPTANCE.md) for the exact scope and test cases.
