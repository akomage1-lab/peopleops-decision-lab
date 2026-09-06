# PeopleOps Decision Lab — Interview Cheatsheet

## Project in one sentence

A public, synthetic, aggregate workforce-planning system that forecasts six-month staffing risk, optimizes constrained hiring starts, and shows bounded resource sensitivity.

## Problem

Reporting a staffing gap does not determine which starts are feasible when budget, recruiter capacity, and lead times interact across roles and months.

## Key model

Department × Role × Month over Jan–Jun 2026. The model converts annual attrition to monthly attrition, forecasts FTE, measures understaffed FTE-months, and selects integer hiring starts under company-wide budget and monthly capacity.

## Stack

React, TypeScript, Vite, FastAPI, Python, PostgreSQL, SQLAlchemy, Alembic, OR-Tools/SCIP with CBC fallback, Vitest, Playwright, GitHub Actions, Vercel, Railway, and Neon.

## Hardest technical decision

Preserving one authoritative optimizer path. Production optimization and M11 sensitivity both assemble the same persisted inputs and use the same fail-closed solver validation rather than duplicating solver mathematics.

## Most important product decision

Keep scope aggregate and explicit. The tool supports staffing-capacity scenario analysis; it does not score people, candidates, role importance, or business strategy.

## Why lexicographic optimization?

The primary goal is lower understaffing. Spend only breaks ties among plans with the same staffing outcome, so cost does not silently trade away the stated staffing objective. The second pass preserves the first within `1e-7` numerical tolerance.

## Why not AI?

The central task is a transparent constrained allocation problem with defined inputs and verifiable invariants. A mixed-integer model makes the objective and constraints inspectable; no LLM is needed or used in the product.

## Why synthetic data?

It enables a public, reproducible portfolio project without exposing employee, candidate, compensation, or company-operational data. It also keeps the model’s scope and limits visible.

## What does Optimal mean?

No feasible plan under the stated six-month model, scenario assumptions, budget, capacity, and lead times has lower total understaffing. It is not a universal strategic, revenue, role-priority, or candidate-quality judgment.

## What is M11 sensitivity?

An on-demand local analysis that reruns the same proven optimizer at budget 50%, 75%, 100%, 125%, and 150%, and capacity -1, submitted, and +1 start per month. It checks monotonicity and labels results as tested local changes, not causal effects or bottlenecks.

## Biggest limitation

The model intentionally omits uncertainty, productivity ramps, skill scarcity, interview capacity, role criticality, revenue impact, and governance or legal review. The result is decision support under explicit assumptions, not a complete workforce strategy.

## What would you improve if this were a real company product?

Start with validated organizational inputs and governance, then add uncertainty modeling, fairness/legal review, richer operational constraints, and carefully controlled integrations. Each addition would need a clear decision contract and evidence that it improves the model rather than adding feature bloat.
