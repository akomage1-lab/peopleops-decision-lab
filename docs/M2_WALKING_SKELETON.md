# M2 Walking Skeleton

## Implemented architecture

M2 intentionally provides one complete local workflow and nothing more:

`PostgreSQL seed data → SQLAlchemy 2 records → FastAPI → existing peopleops forecast/optimizer → typed API response → React/Vite page`

The M1 engine remains in `src/peopleops/`. The API adapter in `api/app/service.py` converts persisted aggregate inputs to the existing `peopleops.models.Scenario`, calls `forecast_workforce` and `optimize_hiring_plan`, and returns their result. It does not reproduce forecasting or solver logic.

PostgreSQL stores only a scenario and the role-level M1 inputs: current FTE, attrition, six targets, lead time, monthly loaded cost, in-flight arrivals, plus scenario-level planning-period incremental workforce budget and monthly recruiting capacity. There are no people, candidates, users, organizations, or HR workflow tables.

## Local PostgreSQL setup

This development environment did not have PostgreSQL or Docker. PostgreSQL 16 was installed locally with Homebrew; the application itself is not containerized.

```bash
brew install postgresql@16
/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D /opt/homebrew/var/postgresql@16 -l /tmp/peopleops-postgres.log start
/opt/homebrew/opt/postgresql@16/bin/createdb peopleops_decision_lab
```

The default application URL uses the current local PostgreSQL user over a Unix socket:

```bash
postgresql+psycopg:///peopleops_decision_lab
```

Set `DATABASE_URL` if your local connection differs.

## Install, migrate, and seed

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m api.seed
```

The seed is deterministic and idempotent. It recreates scenario ID 1 and its three M2 aggregate role rows, plus the separate M3 aggregate demo organization described in [the demo data story](DEMO_DATA_STORY.md).

## Run the walking skeleton

In one terminal:

```bash
.venv/bin/uvicorn api.app.main:app --reload
```

In another:

```bash
cd web
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`. Vite proxies `/api` to FastAPI on port 8000. The page loads scenario 1, displays its six-month planning-period incremental workforce budget, submits a transient budget override, and displays baseline/optimized FTE-months, improvement, spend, recommended starts/arrivals, and safe solver statuses.

## API surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status": "ok"}`. |
| `GET` | `/api/scenarios/1` | Returns the seeded scenario and its aggregate inputs. |
| `POST` | `/api/scenarios/1/optimize` | Runs the existing M1 engine. Optional JSON field: `planning_period_incremental_workforce_budget` (nonnegative). |

`decision_month` and `arrival_month` in optimization responses are one-based for browser display. A submitted override never writes back to PostgreSQL.

## Verification

For PostgreSQL-backed integration tests, create a separate local test database once:

```bash
/opt/homebrew/opt/postgresql@16/bin/createdb peopleops_decision_lab_test
M2_TEST_DATABASE_URL=postgresql+psycopg:///peopleops_decision_lab_test .venv/bin/python -m pytest -q
```

The M2 fixture downgrades and reapplies the Alembic migrations, then seeds the test database. It validates health, retrieval from PostgreSQL, transient budget overrides, invalid-budget rejection, spend constraint, direct M1-engine equivalence, and idempotent seeding.

For the frontend:

```bash
cd web
npm run test
npm run build
```

## M2 limitations

- Exactly one deterministic scenario is seeded; no scenario editor or multiple-scenario workflow exists.
- The only browser-editable input is the planning-period incremental workforce budget.
- There is no authentication, API persistence of overrides, navigation, dashboard, charts, user data, ATS, or payroll scope.
- Solver failures are surfaced as a safe API error; raw solver internals are not exposed.

## Acceptance results

- Fresh PostgreSQL migrations and deterministic seed: passed locally.
- FastAPI reads PostgreSQL, invokes the existing M1 engine, and returns budget-constrained results: passed.
- React scenario fetch, successful optimization flow, and API-error state: covered by two focused frontend tests.
- Python suite: 31 passing tests (24 preserved M1/M1.1 plus 7 M2 tests).
- Frontend test suite: 2 passing tests; TypeScript/Vite production build passes.
