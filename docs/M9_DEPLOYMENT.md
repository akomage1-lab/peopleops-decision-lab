# M9.2 Deployment Runbook

This is the exact deployment handoff for the existing M0–M8 application. It is intentionally a runbook only: M9.1 does **not** create a GitHub repository, cloud database, Railway service, Vercel project, deployment, secret, or public URL.

## Target topology

| Component | Provider | Production responsibility |
| --- | --- | --- |
| React/Vite frontend | Vercel | Builds `web/` as a static site and supplies `VITE_API_BASE_URL`. |
| FastAPI backend | Railway | Runs the root `Procfile` web process, serves `/health` and `/api`, and receives `DATABASE_URL` and explicit CORS origins. |
| PostgreSQL | Neon | Stores Alembic-managed schema and deterministic synthetic aggregate demo data. |

No Docker image, startup-time migration, or startup-time seeding is part of this release design.

## 0. Preflight

1. Start from the approved M9.1 commit and a clean working tree.
2. Choose stable, lowercase project names before creating services, for example `<github-owner>/peopleops-decision-lab`, `<railway-service>`, and `<vercel-project>`. This makes the expected Vercel origin known before the backend starts: `https://<vercel-project>.vercel.app`.
3. Confirm the local checks from the README pass: Python suite, frontend tests, TypeScript check, production build, migration/seed rehearsal, and live Playwright workflow.
4. Review `.env.example`, `web/.env.example`, and `git status`; never add a real `.env`, `web/.env.local`, database URL, token, or generated build output to Git.

## 1. Create and push the GitHub repository

1. Create an empty GitHub repository named `peopleops-decision-lab`; do not initialize it with a README, `.gitignore`, or license if this local repository is the source of truth.
2. From the local repository, set the GitHub remote and push the approved branch/default branch according to the intended branch policy.
3. Open the Actions tab and confirm the committed CI workflow runs. It must validate migrations plus deterministic seed, full Python tests, frontend tests, type check, production build, and the live PostgreSQL/FastAPI/Vite Playwright suite.
4. Keep secrets out of Actions for this project. The application has no GitHub Action deployment step; provider dashboards receive runtime configuration directly.

## 2. Create Neon PostgreSQL and deliberately initialize it

1. Create a Neon project and a database for this demo. Copy the provider connection string only into a password manager or provider environment-variable field.
2. The backend accepts a standard hosted URL beginning with either `postgresql://` or legacy `postgres://`; it converts it to SQLAlchemy's installed `postgresql+psycopg://` dialect while preserving query options such as `sslmode=require`.
3. Run the following **once for initial synthetic-demo initialization** from a trusted local shell. Substitute the real URL only in the shell environment; do not place it in a committed file.

   ```bash
   DATABASE_URL='postgresql://<user>:<password>@<host>/<database>?sslmode=require' \
     .venv/bin/python -m alembic upgrade head
   DATABASE_URL='postgresql://<user>:<password>@<host>/<database>?sslmode=require' \
     .venv/bin/python -m api.seed
   ```

4. `alembic upgrade head` is the intentional schema-release step. `api.seed` recreates the deterministic synthetic dataset and must be an explicit operator action—not a FastAPI startup hook or Railway start command. Repeat seeding only when deliberately resetting this demo data.
5. Save the resulting **single** database URL as Railway's `DATABASE_URL`. Do not expose it to the frontend, Vercel, browser, client code, logs, or documentation.

## 3. Create Railway FastAPI service

1. Create a Railway service from the GitHub repository, using the repository root as its source directory.
2. Let Railway use the root [Procfile](../Procfile):

   ```procfile
   web: sh -c 'uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}'
   ```

   The provider injects `PORT`; the fallback only supports local process checks. The service must not be configured to run migration or seed commands at application startup.
3. Configure the build command as `python -m pip install .` (or Railway's equivalent standard Python build using the root `pyproject.toml`). The runtime dependencies include FastAPI, Uvicorn, SQLAlchemy, psycopg, and OR-Tools.
4. In Railway Variables, set exactly:

   | Variable | Value |
   | --- | --- |
   | `APP_ENV` | `production` |
   | `DATABASE_URL` | Neon hosted PostgreSQL URL; secret |
   | `ALLOWED_ORIGINS` | `https://<vercel-project>.vercel.app` (and only any intentional additional production domain, comma-separated) |

   Do not set `ALLOWED_ORIGINS=*`. Credentials are disabled in the API CORS policy; this public demo does not use browser cookies or authorization headers.
5. Deploy, then confirm `https://<railway-domain>/health` responds `200` with `{"status":"ok"}`. Inspect Railway logs only for normal startup and concise failures; they must not contain a connection string, secret, request payload, or traceback exposed to users.

## 4. Create Vercel static frontend

1. Import the same GitHub repository into Vercel.
2. Set **Root Directory** to `web`.
3. Use `npm ci` as the install command and `npm run build` as the build command. Vite emits the static production bundle to `web/dist`.
4. In Vercel's production environment variables, set:

   | Variable | Value |
   | --- | --- |
   | `VITE_API_BASE_URL` | `https://<railway-domain>` |

   Use the API origin only—no trailing `/api` and no secret. `VITE_*` values are deliberately compiled into the public frontend bundle, so only public HTTPS origins belong there.
5. Deploy and record the resulting URL. If it differs from the planned `https://<vercel-project>.vercel.app`, update Railway `ALLOWED_ORIGINS` to the exact deployed origin and redeploy Railway before accepting browser traffic.

## 5. Final CORS and configuration check

From a browser on the deployed Vercel origin:

1. Confirm a `GET` and an optimization `POST` succeed to the Railway API.
2. Inspect the preflight/response headers. `Access-Control-Allow-Origin` must equal the exact Vercel origin, never `*`; `Access-Control-Allow-Credentials` must be absent.
3. Confirm a request with an unrelated `Origin` does not receive an allow-origin header.
4. Confirm no production bundle references `127.0.0.1`, `localhost`, a private database host, or a committed credential. Development-only Vite proxy references are permitted in `web/vite.config.ts`.

## 6. Production acceptance workflow

Perform this once against the real deployed Vercel URL, using only the synthetic seeded demo:

1. Load the Overview; verify aggregate current-position and six-month risk content appears without a browser console error.
2. Open the Decision Lab and verify the persisted baseline forecast loads.
3. Adjust one clearly valid transient role assumption and verify scenario status becomes dirty.
4. Recompute the scenario forecast; verify the scenario result and baseline/scenario comparison update.
5. Set a valid planning-period incremental workforce budget and six valid monthly recruiting capacities; choose values that produce an optimization recommendation for the seeded data.
6. Click **Optimize Plan**. Verify baseline, scenario, and optimized forecast values render; solver status is `OPTIMAL` for both passes; recommendations show start and arrival month; spend does not exceed submitted budget; starts do not exceed monthly capacity; and no arrival is beyond Month 6.
7. Use **Reset scenario**. Verify the baseline values return and no transient browser edit was persisted.
8. Check desktop and narrow mobile widths: primary navigation, scenario controls, optimize action, result/error states, and horizontally scrollable dense tables remain reachable.
9. Review Railway health/logs and Neon connection/usage dashboards after the workflow. Stop and investigate any API error, solver failure, CORS error, leaked secret, unexpected write, or non-`OPTIMAL` status.

## Operational boundaries

- This is a small public, synthetic portfolio demo. Keep the Railway service always on only while that trade-off is acceptable; review provider usage, spending, and sleep/always-on settings before enabling public access.
- The database seed is deterministic but destructive to the demo dataset it owns; it is suitable for initialization/reset of this synthetic project, not for customer data.
- There is no authentication, tenant isolation, rate limiting, background queue, audit log, or operational monitoring service. Do not represent this deployment as production HR infrastructure.
- Any future domain, analytics, authentication, user data, model behavior, or feature change is outside M9.1/M9.2 release preparation and requires separate scope and security review.
