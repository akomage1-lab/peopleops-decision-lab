# PeopleOps Decision Lab — Portfolio Case Study

## 1. The problem

A workforce planner can know expected attrition, staffing targets, hiring lead times, a budget, and recruiter capacity and still face a difficult allocation decision: which roles should start hiring now, and when, to reduce staffing shortfalls over the next six months? A spreadsheet can report a gap. A dashboard can show trend lines. Neither, by itself, solves the constrained allocation problem when every start competes for the same budget and monthly recruiting capacity and arrives only after a role-specific lead time.

PeopleOps Decision Lab makes that decision explicit. It forecasts aggregate staffing capacity, lets a user alter a small set of assumptions, and selects integer hiring starts that minimize cumulative understaffing under the stated model. It then shows the constraints, timing, spend, and optimization status behind the result rather than treating a recommendation as self-explanatory.

## 2. Product decision

I deliberately kept the product narrow: aggregate workforce planning over a fixed six-month horizon. It has no employee or candidate records, ATS workflow, AI feature, opaque priority score, or claim to choose a company’s strategy. The inputs are deterministic synthetic planning assumptions at Department × Role × Month.

That scope is a product choice, not an omission hidden behind a prototype. A narrow model makes the decision contract inspectable: users can see what is modeled, what is held fixed, and what remains outside the result. It also avoids turning a workforce-planning demonstration into an employment decision system about people.

## 3. Planning model

FTE means full-time-equivalent staffing capacity. If a team is one FTE below its target for one month, that is one understaffed FTE-month; lower cumulative understaffing is better. The baseline projects the persisted synthetic assumptions. A scenario applies transient role-level changes to attrition or staffing targets. An optimized plan adds selected hiring starts to that same scenario.

The model converts annual expected attrition to an equivalent monthly rate. Each planning month applies attrition, then adds in-flight arrivals and new hires whose whole-month lead time has elapsed. A start is an integer decision, so the model does not imply fractional hires. It respects role lead times, a company-wide planning-period incremental workforce budget, and company-wide monthly recruiting capacity.

The solver uses a two-pass lexicographic objective. First, it minimizes total understaffed FTE-months across Jan–Jun 2026. Second, among plans tied on that staffing result, it minimizes modeled in-horizon spend while preserving the first-pass result within a `1e-7` numerical tolerance. A selected hire consumes its role’s modeled monthly loaded workforce cost from arrival through the end of the horizon. That is deliberately not presented as a salary, benefits, recruiting-fee, or total-compensation estimate.

## 4. Architecture

The browser layer is React, TypeScript, and Vite because the product needs a focused interactive decision surface: view the baseline, alter a scenario, run a plan, and inspect the explanation. The frontend calls a typed FastAPI API rather than embedding model logic in the browser.

FastAPI and Python assemble persisted aggregate planning inputs, validate transient requests, and expose baseline, scenario, optimization, and sensitivity results. PostgreSQL stores the deterministic synthetic data, while SQLAlchemy and Alembic make the data model and migration path explicit. OR-Tools runs the mixed-integer optimization, using SCIP with an explicit CBC fallback.

The production architecture keeps those roles separated. Vercel hosts the static frontend; Railway runs the API; Neon hosts PostgreSQL. This is a full live path, not a mocked frontend demo, so the deployment also tests CORS, environment configuration, migrations, seeds, and browser-to-optimizer integration.

## 5. Building trust into optimization

An optimization result is only useful if a reviewer can understand its contract. The Decision Audit states the modeled goal, submitted budget and capacity, lead-time treatment, before-and-after understaffing, and solver status. The recommendation table shows hiring start and arrival timing rather than hiding it in a single score.

Here, **Optimal** has a narrow, testable meaning: no feasible plan under the stated assumptions and constraints has lower total understaffing. It does not mean a plan is the best strategic business decision, the highest-revenue plan, a ranking of role importance, or a statement about candidate quality. The product also calls out what it does not model, including criticality, revenue impact, skill scarcity, productivity ramps, and legal or fairness review. Those boundaries are part of the result, not fine print.

## 6. Usability iteration

The first usable version was mathematically correct, but structured AI usability auditing and one human first-impression review showed that correct output was not automatically understandable. I treated that as a product problem rather than adding more metrics.

The resulting M10 work clarified the product purpose, defined FTE and FTE-months, distinguished Baseline, Scenario, and Optimized states, and separated role-specific assumptions from company-wide constraints and results. It made budget semantics explicit, added plain-language optimizer trust explanations, and made synthetic-data provenance unmistakable. A final structured usability gate found no remaining Critical or High issue. This was structured AI usability auditing, not a claim of broad human user research.

## 7. Advanced differentiator

M11 adds bounded constraint sensitivity after an optimized plan. It reruns the same proven production optimizer, holding the scenario fixed while testing budget at 50%, 75%, 100%, 125%, and 150% of the submitted amount. It separately tests recruiting capacity at one start below, equal to, and one start above the submitted vector for each month, flooring at zero and deduplicating identical vectors.

Each point must pass the same validation and prove both optimization passes optimal. The service checks the expected monotonicity invariant: more tested budget or capacity cannot worsen the minimum understaffing result within numerical tolerance. The UI labels the submitted points and presents one local comparison of +25% budget and +1 recruiting start per month.

This is useful because it turns a single plan into a bounded tradeoff discussion: under these assumptions, how does the best modeled result change when a resource changes? It is intentionally local sensitivity analysis. It does not claim causality, a smooth relationship between discrete points, or that a constraint is a bottleneck unless that is mathematically established.

## 8. Reliability and validation

The project uses a deterministic seed so the browser, API, forecast, and optimizer have a repeatable foundation. Backend regression and integration tests cover validation, cost and horizon semantics, solver status, lexicographic behavior, and sensitivity invariants. Frontend unit tests exercise the decision states and error handling; TypeScript checks and production builds catch integration errors; Playwright executes the live browser path.

GitHub Actions runs the backend and browser workflow in a clean environment. The production optimizer fails closed: a point without proven optimal primary and secondary solves is not silently shown as valid. This matters especially for sensitivity, where a table of alternative points would otherwise look authoritative even if one solve were incomplete.

## 9. What I learned

I learned that translating a business question into an optimization model starts with constraints, definitions, and boundaries—not solver code. I also learned that mathematical correctness and product comprehension are different requirements. The M10 work made that concrete: a user needs to know what is role-specific, what is company-wide, what a cost represents, and what “Optimal” does and does not mean.

I also learned to test invariants instead of only happy paths. For example, the project checks that extra tested budget or capacity cannot worsen the modeled optimum, that end-of-horizon hires are valid, and that the second lexicographic pass preserves the first. Finally, deployment surfaced practical integration work: dependency installation, database URL handling, migrations, CORS, and real browser paths are part of delivering an optimization product, not postscript tasks.

## 10. How I would explain it in an interview

“I built PeopleOps Decision Lab because workforce planning is not only a reporting problem. A planner may know expected attrition, targets, budget, recruiter capacity, and lead times, but still need to decide where and when hiring should start. I modeled that as a six-month aggregate Department-by-Role-by-Month optimization problem and built the full path around it: React for the decision workflow, FastAPI and PostgreSQL for typed synthetic planning inputs, and OR-Tools for a lexicographic mixed-integer solve. I put equal emphasis on trust: the UI shows the goal, constraints, spend, timing, and model limits, and ‘Optimal’ is carefully bounded to the stated model. I then added local sensitivity analysis so a reviewer can see how the same proven optimizer responds to small budget and capacity changes.”

## 11. Three deep-dive interview questions

### 1. Why use optimization instead of a simple ranking?

A ranking can say which role has a large gap, but it cannot choose a globally feasible combination of starts when hires consume shared budget and monthly recruiter capacity and have different arrival times. Mixed-integer optimization evaluates those interactions together.

### 2. What does “Optimal” actually mean here?

It means the solver proved that no feasible plan under the fixed six-month model, submitted constraints, targets, attrition assumptions, and lead times has lower total understaffed FTE-months. It is not a universal strategic recommendation.

### 3. How did you make sure more budget or capacity could not make the result worse?

The feasible set with more of either resource contains the smaller-resource feasible set, so the minimum cannot be worse. M11 reruns the same optimizer at ordered points and tests that invariant within the documented `1e-7` tolerance, while allowing plateaus from integer decisions or another limiting constraint.
