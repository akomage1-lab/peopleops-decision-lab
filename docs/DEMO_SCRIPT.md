# PeopleOps Decision Lab — Demo Script

## 0:00–0:20 — Problem

**Show:** The landing page and product title.

**Say:** “This is PeopleOps Decision Lab, a synthetic aggregate workforce-planning project. It addresses a narrow question: given staffing targets, attrition, lead times, budget, and recruiting capacity, where and when should hiring start to reduce six-month staffing shortages?”

## 0:20–0:45 — Overview

**Show:** Overview metrics, forecast, and department-risk content.

**Say:** “The Overview establishes the persisted baseline. The data is synthetic and aggregate, and the forecast shows staffing capacity against targets over the fixed six-month planning horizon. This is context for a decision, not an employee-level HR record.”

## 0:45–1:15 — Scenario

**Click/show:** Open **Decision Lab**, select a role, change annual expected attrition or one staffing target, then select **Run Scenario**.

**Say:** “Scenario controls are role-specific and transient, so I can test an assumption without changing the baseline. The comparison remains company-wide because one role change can affect the overall planning result.”

## 1:15–1:50 — Optimization

**Click/show:** Point to company-wide budget and monthly recruiting capacity, then select **Optimize Scenario**.

**Say:** “The optimizer chooses integer hiring starts across all roles. It respects the company-wide budget, company-wide monthly recruiting capacity, and each role’s lead time. It first minimizes cumulative understaffed FTE-months; among tied plans, it minimizes modeled in-horizon spend.”

## 1:50–2:15 — Decision Audit

**Show:** Decision Audit and recommended-starts table.

**Say:** “I made the result auditable rather than just showing a recommendation. This section states the goal, constraints, before-and-after understaffing, and solver status. The table makes start and arrival timing visible. ‘Optimal’ means no feasible plan under this stated model has lower total understaffing—it is not a strategic-priority or candidate-quality judgment.”

## 2:15–2:45 — Constraint Sensitivity

**Click/show:** Select **Analyze constraint sensitivity**, then show Budget frontier, capacity table, and Local takeaway.

**Say:** “This advanced follow-up reruns the same proven optimizer at a small set of alternative budget and recruiting-capacity levels. It shows local sensitivity under the same scenario assumptions. I describe these as tested changes, not causal effects or a claim that one constraint is the bottleneck.”

## 2:45–3:00 — Close

**Show:** Model-boundary content or return to the result.

**Say:** “The project demonstrates full-stack decision engineering: a transparent planning model, mixed-integer optimization, explicit trust boundaries, automated validation, and a live deployment. It is intentionally a synthetic aggregate portfolio project, not a production HR system.”
