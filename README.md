# PeopleOps Decision Lab — Workforce Planning & Optimization

PeopleOps Decision Lab is a small, synthetic, aggregate workforce-planning proof of concept. It combines an executive Overview with a Decision Lab: managers can inspect current and projected staffing risk, then model transient assumptions and optimize in-horizon hiring starts.

It is deliberately not an HR CRUD application. It contains no employee or candidate records, authentication, payroll workflow, or real-world customer data.

## Technology and architecture

`PostgreSQL → SQLAlchemy/Alembic → FastAPI → existing M1 forecast/optimizer → React/Vite`

- **Overview:** authoritative M3 observed analytics plus the persisted M4 six-month baseline forecast.
- **Decision Lab:** transient role assumptions, planning-period incremental workforce budget, and monthly recruiting capacity sent to the existing M5/M1 optimizer.
- **Data:** deterministic aggregate demo data, seeded locally; no personal data.

The M1 objective first minimizes total understaffed FTE-months and then minimizes planning-period incremental workforce spend among plans within the documented numerical tolerance of that shortage optimum. Spend covers optimized-hire workforce/payroll cost incurred only after arrival inside the six-month planning horizon.

## Supported environment

- Python 3.9 or later (CI validates Python 3.9).
- Node.js 20 or later for the frontend and browser checks.
- PostgreSQL 16 (local PostgreSQL or the CI service image).

Python dependencies are bounded in [pyproject.toml](pyproject.toml); frontend installs are pinned by [web/package-lock.json](web/package-lock.json) and should use `npm ci`.

## Clean local setup

Copy the safe local defaults if you need environment variables; do not commit a real `.env` file:

```bash
cp .env.example .env
```

Start a local PostgreSQL 16 server and create the development and test databases. The existing local setup documentation uses Homebrew:

```bash
brew install postgresql@16
/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D /opt/homebrew/var/postgresql@16 -l /tmp/peopleops-postgres.log start
/opt/homebrew/opt/postgresql@16/bin/createdb peopleops_decision_lab
/opt/homebrew/opt/postgresql@16/bin/createdb peopleops_decision_lab_test
```

From the repository root, install the backend, apply the schema, and seed deterministic demo data:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m api.seed
```

The seed is idempotent: it recreates the deterministic aggregate M3 organization and M2 scenario. For a clean schema rehearsal, run `.venv/bin/python -m alembic downgrade base` followed by `.venv/bin/python -m alembic upgrade head` before seeding.

In separate terminals, run the API and frontend:

```bash
DATABASE_URL=postgresql+psycopg:///peopleops_decision_lab .venv/bin/python -m uvicorn api.app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd web
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` requests to FastAPI on port 8000.

## Verification

Run backend integration/regression tests against the separate test database:

```bash
M2_TEST_DATABASE_URL=postgresql+psycopg:///peopleops_decision_lab_test .venv/bin/python -m pytest -q
```

Run frontend tests, type checking, and production build:

```bash
cd web
npm ci
npm test
npm run typecheck
npm run build
```

For live browser acceptance, with PostgreSQL, API, and Vite already running, install Chromium once and execute the critical flows against the real backend:

```bash
cd web
npx playwright install chromium
npm run e2e
```

GitHub Actions runs the migration/seed/backend suite, frontend unit/type/build checks, and these live browser flows against PostgreSQL. See [M8 reliability notes](docs/M8_RELIABILITY.md).

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

M2 introduced the local end-to-end backbone: a seeded PostgreSQL scenario is read by FastAPI, adapted into the unchanged M1 engine, and displayed in React/Vite. Later milestones expanded the browser Decision Lab with transient role assumptions, budget, and recruiting-capacity edits; no browser edits are persisted.

See [M2 walking-skeleton setup and run instructions](docs/M2_WALKING_SKELETON.md). Once PostgreSQL is running and migrated, start the API with `.venv/bin/uvicorn api.app.main:app --reload`, then run `npm run dev` in `web/` and open the shown local URL.

## M3 data and metrics foundation

M3 adds a deterministic, aggregate 12-month workforce history and six months of planning assumptions. Read-only APIs expose a workforce summary, historical trend, and department metrics; the M2 page deliberately remains unchanged. See [the M3 metric contract](docs/M3_METRICS.md) and [the synthetic demo-data story](docs/DEMO_DATA_STORY.md).

## M4 production forecast engine

M4 adapts persisted aggregate workforce observations and explicit future assumptions into the unchanged M1 baseline forecast engine. `GET /api/workforce/forecast` returns typed role-month forecasts, additive department and organization aggregates, and the provenance needed to explain them. See [the M4 production forecast contract](docs/M4_PRODUCTION_FORECAST.md).

## M5 production workforce optimizer

M5 adapts the same persisted M3/M4 inputs into the unchanged M1 two-pass optimizer. `POST /api/workforce/optimize` requires an explicit planning-period incremental workforce budget and six monthly recruiting-capacity values, returning provenance, baseline/optimized forecasts, and validated recommendations. See [the M5 production optimizer contract](docs/M5_PRODUCTION_OPTIMIZER.md).

## M6 Decision Lab

M6 adds the transient planning workflow: persisted baseline, editable scenario, authoritative scenario forecast, production optimization, three-way comparison, and deterministic explainability. See [the Decision Lab contract](docs/M6_DECISION_LAB.md) and [the canonical demo flow](docs/M6_DEMO_FLOW.md).

## M7 Executive Workforce Analytics

M7 adds a compact executive Overview before the Decision Lab. `GET /api/workforce/overview` composes authoritative M3 observed analytics and the persisted M4 baseline forecast into current position, six-month risk concentration, recent workforce flow, historical hiring-speed evidence, and clearly separated observed and forecast visuals. See [the M7 executive analytics contract](docs/M7_EXECUTIVE_ANALYTICS.md).

## M8 reliability and quality hardening

M8 adds reproducible CI, deterministic browser acceptance coverage, safe database-failure handling, accessibility and responsive-layout checks, and public-repository configuration safeguards. See [the M8 reliability guide](docs/M8_RELIABILITY.md).

## Limitations and assumptions

- The horizon is fixed to six months, and all inputs are synthetic aggregate expectations.
- Attrition is deterministic expected FTE, not employee-level stochastic simulation.
- New hires join fully at the end of a whole-month lead time; partial-month starts and productivity ramps are excluded.
- Costs are a simple loaded monthly cost charged from arrival through the end of M1. The planning-period incremental workforce budget therefore represents only optimized-hire workforce/payroll spend incurred inside the six-month horizon; existing and in-flight workforce costs are excluded.
- The model has one aggregate recruiting-capacity constraint per month. It does not yet model source channels, interviewer capacity, geographic constraints, or role-specific recruiting caps.
- A plan is only trusted if both solver passes terminate `OPTIMAL`; failures raise rather than return a guessed recommendation.

See [the frozen M0 contract](docs/PROJECT_CONTRACT.md) and [the M1 acceptance criteria](docs/M1_ACCEPTANCE.md) for the exact scope and test cases.
