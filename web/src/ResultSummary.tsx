import { ProductionForecast, ProductionOptimizationResult, ScenarioForecast } from "./api";

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const fteMonths = (value: number) => value.toFixed(1);

type RunningAction = "scenario" | "optimize" | null;

type ResultSummaryProps = {
  baseline: ProductionForecast;
  scenario: ScenarioForecast | null;
  optimized: ProductionOptimizationResult | null;
  runningAction: RunningAction;
};

export function ResultSummary({ baseline, scenario, optimized, runningAction }: ResultSummaryProps) {
  const totalHires = optimized?.recommendations.reduce((sum, recommendation) => sum + recommendation.hires, 0) ?? 0;
  const scenarioDelta = scenario ? scenario.total_understaffed_fte_months - baseline.total_understaffed_fte_months : null;
  const optimizedDelta = optimized && scenario ? optimized.optimized_understaffed_fte_months - scenario.total_understaffed_fte_months : null;
  const solverOptimal = optimized?.primary_status === "OPTIMAL" && optimized.secondary_status === "OPTIMAL";
  const status = runningAction === "scenario" ? "Recalculating scenario…" : runningAction === "optimize" ? "Building optimized plan…" : optimized ? "Optimized plan ready" : "Scenario ready";
  const deltaLabel = (delta: number, comparison: string) => delta <= 0 ? `↓ ${fteMonths(Math.abs(delta))} vs ${comparison}` : `↑ ${fteMonths(delta)} higher than ${comparison}`;

  return <aside className={`result-summary${optimized ? " has-optimized" : " has-scenario"}${runningAction ? " is-running" : ""}`} aria-label="Current plan summary" aria-live="polite" aria-busy={Boolean(runningAction)}>
    <div className="result-summary-top"><span className="section-kicker">Current result</span><strong>{status}</strong></div>
    <div className="result-summary-flow" aria-label="Understaffing progression">
      <div><span>Baseline</span><strong>{fteMonths(baseline.total_understaffed_fte_months)}</strong></div>
      {scenario && <><span className="result-summary-arrow" aria-hidden="true">→</span><div><span>Scenario</span><strong>{fteMonths(scenario.total_understaffed_fte_months)}</strong></div></>}
      {optimized && <><span className="result-summary-arrow" aria-hidden="true">→</span><div><span>Optimized</span><strong>{fteMonths(optimized.optimized_understaffed_fte_months)}</strong></div></>}
    </div>
    <div className="result-summary-meta">
      {scenarioDelta !== null && <span className={`summary-delta ${scenarioDelta <= 0 ? "is-positive" : "is-warning"}`}>{deltaLabel(scenarioDelta, "baseline")}</span>}
      {optimizedDelta !== null && <span className={`summary-delta ${optimizedDelta <= 0 ? "is-positive" : "is-warning"}`}>{deltaLabel(optimizedDelta, "scenario")}</span>}
      {optimized && <><span>Spend {currency.format(optimized.planning_period_incremental_workforce_spend_used)} / {currency.format(optimized.submitted_budget)}</span><span>{totalHires} hire {totalHires === 1 ? "start" : "starts"}</span><span className="summary-status">{solverOptimal ? "Optimal" : optimized.primary_status}</span></>}
    </div>
  </aside>;
}
