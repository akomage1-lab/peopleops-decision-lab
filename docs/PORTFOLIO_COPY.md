# Portfolio Copy

## One sentence

PeopleOps Decision Lab is a synthetic workforce-planning demo that explains six-month staffing risk and optimizes constrained hiring starts using aggregate data.

## Short project description

PeopleOps Decision Lab combines a React decision interface, FastAPI service, PostgreSQL-backed deterministic demo dataset, and an OR-Tools optimization model. Users can inspect staffing risk, change transient planning assumptions, and compare a baseline with an optimized hiring plan under explicit budget, lead-time, and recruiting-capacity constraints. It is intentionally a portfolio proof of concept: all data is synthetic and aggregate, and the tool does not make employment decisions about people.

## Technical description

The application serves observed workforce analytics and a six-month forecast from PostgreSQL through FastAPI, then invokes the existing M1 mixed-integer optimizer for scenario-specific hiring recommendations. The model works at Department × Role × Month and solves lexicographically: first it minimizes understaffed FTE-months, then it minimizes in-horizon incremental workforce spend while preserving the shortage optimum within a documented numerical tolerance. FastAPI returns typed baseline, scenario, and optimized results to a React/Vite interface; Alembic migrations, deterministic seeding, integration tests, frontend tests, and Playwright cover the live path.

## Résumé bullets

- Built a full-stack workforce-planning portfolio demo with React, TypeScript, FastAPI, PostgreSQL, Alembic, and OR-Tools; traced the browser workflow through a live seeded database and optimizer.
- Implemented and tested a lexicographic mixed-integer hiring-plan solve that minimizes six-month understaffing before in-period workforce spend, subject to hiring lead times, budget, and monthly recruiting capacity.
- Prepared an environment-driven release path for Vercel, Railway, and Neon with explicit production CORS, health checks, deterministic migration/seed procedures, CI, and browser-level regression coverage.

## Responsible-use statement

This is a synthetic, aggregate scenario-analysis demo—not an HR system, source of record, or automated employment decision-maker. Results require human review and do not replace legal, fairness, financial, or operational judgment.
