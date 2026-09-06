# Portfolio Copy

## One-line version

Built a public workforce-planning decision system that forecasts staffing risk, optimizes constrained hiring starts, and explains bounded budget and recruiting-capacity tradeoffs.

## 50-word version

PeopleOps Decision Lab is a full-stack workforce-planning portfolio project built with React, FastAPI, PostgreSQL, and OR-Tools. It forecasts six-month aggregate staffing shortages, supports transient role-level scenarios, solves integer hiring starts under budget, capacity, and lead-time constraints, audits optimality, and performs bounded local sensitivity analysis. All data is synthetic and aggregate.

## 100-word version

PeopleOps Decision Lab turns workforce planning from a reporting problem into a transparent constrained-decision workflow. A React/TypeScript interface reads a deterministic synthetic aggregate dataset through FastAPI and PostgreSQL, lets a user test role-level attrition and target assumptions, then invokes an OR-Tools mixed-integer model to minimize six-month understaffed FTE-months under company-wide budget, monthly recruiting-capacity, and hiring-lead-time constraints. The interface explains the submitted constraints, optimality, spend, and recommendation timing. A bounded sensitivity analysis reruns the same proven optimizer at alternative budget and recruiting-capacity points. It is a portfolio proof of concept, not an HR system or automated employment decision-maker.

## Technical version

I built a browser-to-database workforce-planning path with React, TypeScript, Vite, FastAPI, PostgreSQL, SQLAlchemy, Alembic, and OR-Tools. The model operates at Department × Role × Month over a fixed six-month horizon and uses a lexicographic mixed-integer solve: first minimize understaffed FTE-months, then minimize in-horizon incremental workforce spend among tied staffing plans. I added typed transient scenario and sensitivity endpoints, fail-closed optimality validation, deterministic seeding, Python regression tests, Vitest, Playwright, GitHub Actions, and production deployment on Vercel, Railway, and Neon.

## HR / business version

PeopleOps Decision Lab demonstrates how workforce-planning assumptions can become a transparent decision process rather than a static dashboard. A planner can see aggregate staffing risk, test a role-level attrition or target change without changing the baseline, and evaluate a constrained hiring plan with its spend, timing, and modeled staffing improvement visible. The tool also shows how that result changes at a small set of alternative budget and recruiting-capacity levels. It intentionally does not score people, candidates, role importance, or business strategy; it supports aggregate scenario analysis under explicit assumptions.

## Resume bullets — recommended

- Built a public full-stack workforce-planning decision system with React/TypeScript, FastAPI, PostgreSQL, and OR-Tools for synthetic aggregate staffing scenarios.
- Implemented a lexicographic mixed-integer optimizer that minimizes six-month understaffing subject to company-wide budget, monthly recruiting capacity, and role hiring lead times.
- Added transparent Decision Audit and bounded sensitivity analysis; validated the live path with Python, frontend, and browser tests and deployed through Vercel, Railway, and Neon.

## Resume bullets — shorter alternative

- Built a React/FastAPI/PostgreSQL workforce-planning system with OR-Tools constrained-hiring optimization.
- Added explainable audit, local constraint sensitivity, CI, and live browser validation for a public synthetic-data deployment.

## Skills / keywords

Workforce Planning; People Analytics; Operations Research; Mixed-Integer Programming; Optimization; Scenario Analysis; Sensitivity Analysis; React; TypeScript; Python; FastAPI; PostgreSQL; SQLAlchemy; Alembic; OR-Tools; SCIP; CI/CD; GitHub Actions; Playwright; Vitest; Vercel; Railway; Neon.

## Responsible-use statement

This is a synthetic, aggregate scenario-analysis portfolio project—not an HR system, source of record, or automated employment decision-maker. Results require human, legal, fairness, financial, and operational review.
