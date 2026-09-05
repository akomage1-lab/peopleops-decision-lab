import { FormEvent, useEffect, useState } from "react";
import { fetchScenario, OptimizationResult, optimizePlan, Scenario } from "./api";
import "./styles.css";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0
});

const fteMonths = (value: number) => value.toFixed(3);

export default function App() {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [budget, setBudget] = useState("");
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);

  useEffect(() => {
    fetchScenario()
      .then((data) => {
        setScenario(data);
        setBudget(String(data.planning_period_incremental_workforce_budget));
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Unable to load scenario."))
      .finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedBudget = Number(budget);
    if (!Number.isFinite(parsedBudget) || parsedBudget < 0) {
      setError("Enter a non-negative planning-period incremental workforce budget.");
      return;
    }
    setError(null);
    setOptimizing(true);
    try {
      setResult(await optimizePlan(parsedBudget));
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Optimization failed.");
    } finally {
      setOptimizing(false);
    }
  }

  if (loading) {
    return <main className="shell"><p>Loading seeded scenario…</p></main>;
  }

  if (scenario === null) {
    return <main className="shell"><p className="error">{error ?? "Scenario unavailable."}</p></main>;
  }

  return (
    <main className="shell">
      <header>
        <p className="eyebrow">PeopleOps Decision Lab · M2</p>
        <h1>{scenario.name}</h1>
        <p>{scenario.planning_horizon_months}-month aggregate workforce plan</p>
      </header>

      <section className="card" aria-labelledby="assumptions-heading">
        <h2 id="assumptions-heading">Assumptions</h2>
        <form onSubmit={submit}>
          <label htmlFor="budget">Planning-period incremental workforce budget</label>
          <div className="action-row">
            <input
              id="budget"
              aria-label="Planning-period incremental workforce budget"
              type="number"
              min="0"
              step="1"
              value={budget}
              onChange={(event) => setBudget(event.target.value)}
            />
            <button type="submit" disabled={optimizing}>
              {optimizing ? "Optimizing…" : "Optimize Plan"}
            </button>
          </div>
        </form>
      </section>

      {error !== null && <p className="error" role="alert">{error}</p>}

      {result !== null && (
        <section className="results" aria-live="polite">
          <div className="metrics">
            <article className="card"><h2>Baseline result</h2><strong>{fteMonths(result.baseline_understaffed_fte_months)}</strong><span>understaffed FTE-months</span></article>
            <article className="card"><h2>Optimized result</h2><strong>{fteMonths(result.optimized_understaffed_fte_months)}</strong><span>understaffed FTE-months</span></article>
            <article className="card"><h2>Improvement</h2><strong>{fteMonths(result.improvement_understaffed_fte_months)}</strong><span>FTE-months reduced</span></article>
          </div>
          <section className="card">
            <h2>Recommended hiring starts</h2>
            <p>Spend used: {currency.format(result.incremental_workforce_spend_used)} of {currency.format(result.available_budget)}</p>
            {result.recommendations.length === 0 ? <p>No optimized hiring starts.</p> : (
              <table>
                <thead><tr><th>Role</th><th>Starts</th><th>Start month</th><th>Arrival month</th><th>In-period spend</th></tr></thead>
                <tbody>{result.recommendations.map((item) => <tr key={`${item.department}-${item.role}-${item.decision_month}`}><td>{item.department} / {item.role}</td><td>{item.hires}</td><td>{item.decision_month}</td><td>{item.arrival_month}</td><td>{currency.format(item.incremental_workforce_spend)}</td></tr>)}</tbody>
              </table>
            )}
            <p className="solver">Solver: {result.solver_status.solver}; primary {result.solver_status.primary}, secondary {result.solver_status.secondary}</p>
          </section>
        </section>
      )}
    </main>
  );
}
