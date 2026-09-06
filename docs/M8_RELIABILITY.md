# M8 Reliability, CI, and Quality Hardening

## CI and test layers

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) contains one
understandable validation workflow:

- **backend-and-e2e** installs bounded Python dependencies on Python 3.9,
  starts PostgreSQL 16, proves downgrade/upgrade plus deterministic seed,
  runs the complete Python suite, then starts FastAPI and Vite and runs the
  Playwright critical flows against the live API and database.
- **frontend** uses `npm ci`, runs Vitest, TypeScript checking, and performs a
  production Vite build.

The browser suite covers: Overview loaded with seeded metrics and navigation;
a changed scenario and reset; a valid optimization and solver status; and
invalid client input with no optimized recommendation displayed. It never mocks
the FastAPI/optimizer path.

## Reproducible environment

Python 3.9+ is supported and CI validates Python 3.9. Dependency ranges in
`pyproject.toml` intentionally retain the compatible OR-Tools/SCIP range.
Frontend dependency resolution is committed in `web/package-lock.json`; use
`npm ci` rather than a floating install for verification.

PostgreSQL 16 is the documented local and CI target. `DATABASE_URL` and the
separate `M2_TEST_DATABASE_URL` are environment-configurable; `.env.example`
contains only local socket defaults. A developer-local `.env` is ignored.

The seed is deterministic and idempotent. It recreates the synthetic M2
scenario and aggregate M3 organization in one transaction. The test fixture
also exercises a downgrade-to-base, upgrade-to-head, and seed before the
integration suite, so tests do not rely on a pre-existing local database.

## Error-handling and logging policy

- Invalid API inputs return FastAPI validation errors or concise 4xx details.
- Incomplete persisted forecast data returns a clear 422; it is never treated
  as zero or forward-filled.
- Solver failure returns a 503 and never a partial or apparently valid hiring
  recommendation.
- SQLAlchemy/database failures are logged server-side and returned as a
  generic 503 message without a connection string or traceback.
- Overview and Decision Lab show loading and concise API/network error states;
  null measurements render as `Not available`, not zero.

The API logs startup and meaningful rejections/failures only. It does not log
secrets, complete request payloads, or personal data.

## Accessibility and responsive checks

- Overview and Decision Lab use semantic headings, native buttons, labels,
  tables with headers, visible keyboard focus, and text error states.
- Charts have accessible names and screen-reader-only data tables so the
  underlying monthly values are available without interpreting color or hover.
- Loading states expose `aria-busy` and polite live text; errors use alerts.
- Desktop, laptop, tablet-ish, and mobile-ish browser checks verify that the
  primary navigation, controls, and tables remain reachable. Tables scroll
  horizontally in narrow containers rather than forcing controls off-screen.

Remaining limitation: this is a compact desktop-oriented planning proof of
concept. Dense scenario and recommendation tables can require horizontal
scrolling on a narrow phone; they are intentionally not redesigned into a
separate mobile application.

## Performance sanity expectations

The seeded API calls are intentionally small and local. On the M8 local
PostgreSQL rehearsal, HTTP timings were approximately **34 ms** for Overview,
**15 ms** for baseline forecast, and **61 ms** for production optimization;
the returned solver timing remains in the expected 50–65 ms range. No
performance tuning is introduced.

## Public-repository audit

- No secrets, private credentials, employee data, or generated build artifacts
  are committed.
- `.env` and variants are ignored; `.env.example` is safe to publish.
- Database configuration is environment-driven and defaults only to a local
  PostgreSQL socket.
- CORS is not opened globally; the Vite development proxy is local-only.
- `npm audit` is reviewed during M8; production dependencies report no known
  vulnerabilities at the validated lockfile state.

## Scope and limitations

M8 changes no workforce metric, forecast transition, optimizer objective,
constraint, cost definition, or product feature. It adds no M9 portfolio work,
AI/LLM functionality, authentication, employee/candidate data, or deployment
infrastructure.
