import { useEffect, useMemo, useState } from "react";
import {
  DepartmentMonth,
  fetchProductionForecast,
  forecastScenario,
  optimizeScenario,
  OrganizationMonth,
  ProductionForecast,
  ProductionOptimizationResult,
  RoleProvenance,
  ScenarioForecast,
  ScenarioRoleOverride
} from "./api";
import "./styles.css";

const DEFAULT_BUDGET = 150000;
const DEFAULT_CAPACITY = [2, 2, 2, 2, 2, 2];
const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const fteMonths = (value: number) => value.toFixed(1);
const monthLabel = (iso: string) => new Intl.DateTimeFormat("en-US", { month: "short" }).format(new Date(`${iso}T12:00:00`));

type OverrideState = Record<number, ScenarioRoleOverride>;

function endMonth(months: OrganizationMonth[]) {
  return months[months.length - 1];
}

function finalDepartmentShortages(months: DepartmentMonth[]) {
  const lastMonth = months[months.length - 1]?.month;
  return months.filter((row) => row.month === lastMonth).sort((left, right) => right.staffing_shortage - left.staffing_shortage).slice(0, 5);
}

function trajectoryPoints(months: OrganizationMonth[], metric: "expected_fte" | "staffing_target", max: number) {
  return months.map((row, index) => `${24 + index * 58},${126 - (row[metric] / max) * 104}`).join(" ");
}

function StaffingTrajectory({ baseline, scenario, optimized }: { baseline: OrganizationMonth[]; scenario?: OrganizationMonth[]; optimized?: OrganizationMonth[] }) {
  const allMonths = [...baseline, ...(scenario ?? []), ...(optimized ?? [])];
  const max = Math.max(...allMonths.map((row) => Math.max(row.expected_fte, row.staffing_target)), 1) * 1.04;
  return (
    <figure className="chart-card" aria-labelledby="trajectory-heading">
      <figcaption><h2 id="trajectory-heading">Organization staffing trajectory</h2><p>Expected FTE compared with staffing target; calculations come from the production APIs.</p></figcaption>
      <svg viewBox="0 0 340 154" role="img" aria-label="Organization staffing trajectory chart">
        <line x1="24" y1="126" x2="320" y2="126" className="chart-axis" />
        <line x1="24" y1="22" x2="24" y2="126" className="chart-axis" />
        <polyline points={trajectoryPoints(baseline, "staffing_target", max)} className="chart-line target" />
        <polyline points={trajectoryPoints(baseline, "expected_fte", max)} className="chart-line baseline" />
        {scenario && <polyline points={trajectoryPoints(scenario, "expected_fte", max)} className="chart-line scenario" />}
        {optimized && <polyline points={trajectoryPoints(optimized, "expected_fte", max)} className="chart-line optimized" />}
        {baseline.map((row, index) => <text key={row.month} x={19 + index * 58} y="145" className="chart-label">{monthLabel(row.month)}</text>)}
      </svg>
      <div className="legend"><span><i className="legend-target" />Target</span><span><i className="legend-baseline" />Baseline</span>{scenario && <span><i className="legend-scenario" />Scenario</span>}{optimized && <span><i className="legend-optimized" />Optimized</span>}</div>
    </figure>
  );
}

function SummaryCard({ label, total, ending, spend }: { label: string; total: number; ending: OrganizationMonth; spend?: number }) {
  return <article className="summary-card"><p>{label}</p><strong>{fteMonths(total)}</strong><span>understaffed FTE-months</span><dl><div><dt>Month 6 expected FTE</dt><dd>{number.format(ending.expected_fte)}</dd></div><div><dt>Month 6 target</dt><dd>{number.format(ending.staffing_target)}</dd></div><div><dt>Month 6 shortage</dt><dd>{number.format(ending.staffing_shortage)}</dd></div>{spend !== undefined && <div><dt>Incremental spend</dt><dd>{currency.format(spend)}</dd></div>}</dl></article>;
}

export default function App() {
  const [baseline, setBaseline] = useState<ProductionForecast | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [overrides, setOverrides] = useState<OverrideState>({});
  const [budget, setBudget] = useState(DEFAULT_BUDGET);
  const [capacity, setCapacity] = useState(DEFAULT_CAPACITY);
  const [scenario, setScenario] = useState<ScenarioForecast | null>(null);
  const [optimized, setOptimized] = useState<ProductionOptimizationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetchProductionForecast()
      .then((data) => {
        setBaseline(data);
        setSelectedRoleId(data.role_provenance.find((role) => role.department === "Sales" && role.role === "Sales Development Representative")?.role_id ?? data.role_provenance[0]?.role_id ?? null);
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Unable to load the production baseline."))
      .finally(() => setLoading(false));
  }, []);

  const selectedRole = useMemo(() => baseline?.role_provenance.find((role) => role.role_id === selectedRoleId) ?? null, [baseline, selectedRoleId]);
  const selectedValues = selectedRole ? overrides[selectedRole.role_id] ?? { role_id: selectedRole.role_id, annual_expected_attrition_rate: selectedRole.annual_expected_attrition_rate, staffing_targets: selectedRole.staffing_targets } : null;
  const roleOverrides = Object.values(overrides);

  function clearResults() {
    setScenario(null);
    setOptimized(null);
  }

  function updateSelectedRole(change: Partial<ScenarioRoleOverride>) {
    if (!selectedValues) return;
    setOverrides((current) => ({ ...current, [selectedValues.role_id]: { ...selectedValues, ...change } }));
    clearResults();
    setError(null);
  }

  function validateInputs() {
    if (!Number.isFinite(budget) || budget < 0) return "Enter a non-negative planning-period incremental workforce budget.";
    if (capacity.length !== 6 || capacity.some((value) => !Number.isInteger(value) || value < 0)) return "Recruiting capacity must contain six non-negative whole numbers.";
    for (const override of roleOverrides) {
      if (!Number.isFinite(override.annual_expected_attrition_rate) || override.annual_expected_attrition_rate < 0 || override.annual_expected_attrition_rate >= 1) return "Annual expected attrition must be at least 0% and below 100%.";
      if (override.staffing_targets.length !== 6 || override.staffing_targets.some((value) => !Number.isFinite(value) || value < 0)) return "Each monthly staffing target must be a finite non-negative value.";
    }
    return null;
  }

  async function runScenario() {
    const validation = validateInputs();
    if (validation) return setError(validation);
    setError(null);
    setRunning(true);
    try {
      setScenario(await forecastScenario(roleOverrides));
      setOptimized(null);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Scenario forecast failed.");
    } finally {
      setRunning(false);
    }
  }

  async function runOptimization() {
    const validation = validateInputs();
    if (validation) return setError(validation);
    if (!scenario) return setError("Run the scenario before optimizing it.");
    setError(null);
    setRunning(true);
    try {
      setOptimized(await optimizeScenario({ planning_period_incremental_workforce_budget: budget, monthly_recruiting_capacity: capacity, role_overrides: roleOverrides }));
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Scenario optimization failed.");
    } finally {
      setRunning(false);
    }
  }

  function resetToBaseline() {
    setOverrides({});
    setBudget(DEFAULT_BUDGET);
    setCapacity(DEFAULT_CAPACITY);
    clearResults();
    setError(null);
  }

  if (loading) return <main className="app-shell" aria-busy="true"><p className="loading" aria-live="polite">Loading the persisted production baseline…</p></main>;
  if (!baseline) return <main className="app-shell"><p className="error" role="alert">{error ?? "Production baseline unavailable."}</p></main>;

  const baselineEnd = endMonth(baseline.organization_months);
  const scenarioEnd = scenario ? endMonth(scenario.organization_months) : null;
  const optimizedEnd = optimized ? endMonth(optimized.optimized_organization_months) : null;
  const largestRecommendation = optimized?.recommendations.slice().sort((left, right) => right.hires - left.hires)[0];

  return <main className="app-shell">
    <header className="hero">
      <p className="eyebrow">PeopleOps Decision Lab</p>
      <h1>Workforce decisions, made explicit.</h1>
      <p>Compare the persisted baseline, a transient planning scenario, and an optimized hiring plan across the next {baseline.planning_horizon_months} months.</p>
    </header>

    {error && <p className="error" role="alert">{error}</p>}

    <section className="baseline-panel" aria-labelledby="baseline-heading">
      <div><p className="section-kicker">1. Baseline</p><h2 id="baseline-heading">Where are we heading?</h2><p>Observed through {baseline.observation_date}; no scenario edits or new optimized hires.</p></div>
      <div className="baseline-stat"><strong>{fteMonths(baseline.total_understaffed_fte_months)}</strong><span>six-month understaffed FTE-months</span></div>
    </section>

    <section className="content-grid">
      <aside className="scenario-panel" aria-labelledby="scenario-heading">
        <div className="panel-heading"><div><p className="section-kicker">2. Scenario inputs</p><h2 id="scenario-heading">What if assumptions change?</h2></div><button type="button" className="text-button" onClick={resetToBaseline}>Reset to Baseline</button></div>
        <p className="helper">Changes are transient. They never write to the production baseline.</p>
        <label htmlFor="role-select">Role to edit</label>
        <select id="role-select" value={selectedRoleId ?? ""} onChange={(event) => setSelectedRoleId(Number(event.target.value))}>
          {baseline.role_provenance.map((role) => <option value={role.role_id} key={role.role_id}>{role.department} · {role.role}</option>)}
        </select>
        {selectedRole && selectedValues && <div className="role-editor">
          <p className="role-meta">Starting FTE {number.format(selectedRole.starting_observed_fte)} · future assumption</p>
          <label htmlFor="attrition">Annual expected attrition</label>
          <div className="suffix-input"><input id="attrition" aria-label="Annual expected attrition" type="number" min="0" max="99.9" step="0.1" value={selectedValues.annual_expected_attrition_rate * 100} onChange={(event) => updateSelectedRole({ annual_expected_attrition_rate: Number(event.target.value) / 100 })} /><span>%</span></div>
          <fieldset><legend>Monthly staffing target</legend><div className="target-grid">{selectedValues.staffing_targets.map((target, index) => <label key={index}>M{index + 1}<input aria-label={`Target month ${index + 1}`} type="number" min="0" step="0.5" value={target} onChange={(event) => { const targets = [...selectedValues.staffing_targets]; targets[index] = Number(event.target.value); updateSelectedRole({ staffing_targets: targets }); }} /></label>)}</div></fieldset>
        </div>}
        <div className="constraint-grid"><label htmlFor="budget">Planning-period incremental workforce budget<input id="budget" aria-label="Planning-period incremental workforce budget" type="number" min="0" step="1000" value={budget} onChange={(event) => { setBudget(Number(event.target.value)); setOptimized(null); }} /></label><fieldset><legend>Monthly recruiting capacity</legend><div className="capacity-grid">{capacity.map((value, index) => <label key={index}>M{index + 1}<input aria-label={`Recruiting capacity month ${index + 1}`} type="number" min="0" step="1" value={value} onChange={(event) => { const next = [...capacity]; next[index] = Number(event.target.value); setCapacity(next); setOptimized(null); }} /></label>)}</div></fieldset></div>
        <div className="action-row"><button type="button" className="secondary" onClick={runScenario} disabled={running}>{running ? "Running…" : "Run Scenario"}</button><button type="button" onClick={runOptimization} disabled={running || !scenario}>{running ? "Optimizing…" : "Optimize Scenario"}</button></div>
      </aside>

      <section className="decision-panel" aria-labelledby="comparison-heading">
        <div className="panel-heading"><div><p className="section-kicker">3. Compare</p><h2 id="comparison-heading">Baseline → Scenario → Optimized plan</h2></div>{scenario && <span className="status">Scenario active</span>}</div>
        <div className="summary-grid"><SummaryCard label="Baseline" total={baseline.total_understaffed_fte_months} ending={baselineEnd} />{scenario && scenarioEnd && <SummaryCard label="Scenario" total={scenario.total_understaffed_fte_months} ending={scenarioEnd} />}{optimized && optimizedEnd && <SummaryCard label="Optimized plan" total={optimized.optimized_understaffed_fte_months} ending={optimizedEnd} spend={optimized.planning_period_incremental_workforce_spend_used} />}</div>
        {scenario && <p className="comparison-note">The scenario {scenario.total_understaffed_fte_months >= baseline.total_understaffed_fte_months ? "adds" : "reduces"} {fteMonths(Math.abs(scenario.total_understaffed_fte_months - baseline.total_understaffed_fte_months))} understaffed FTE-months versus baseline.{optimized && ` Optimization recovers ${fteMonths(scenario.total_understaffed_fte_months - optimized.optimized_understaffed_fte_months)} FTE-months.`}</p>}
        <StaffingTrajectory baseline={baseline.organization_months} scenario={scenario?.organization_months} optimized={optimized?.optimized_organization_months} />
      </section>
    </section>

    <section className="lower-grid">
      <section className="table-panel" aria-labelledby="departments-heading"><p className="section-kicker">Projected gaps</p><h2 id="departments-heading">Largest Month 6 department shortages</h2><table><thead><tr><th>Department</th><th>Expected FTE</th><th>Target</th><th>Shortage</th></tr></thead><tbody>{finalDepartmentShortages((optimized?.optimized_department_months ?? scenario?.department_months ?? baseline.department_months)).map((row) => <tr key={`${row.department}-${row.month}`}><td>{row.department}</td><td>{number.format(row.expected_fte)}</td><td>{number.format(row.staffing_target)}</td><td><span className="gap-value">{number.format(row.staffing_shortage)}</span></td></tr>)}</tbody></table></section>
      <section className="explain-panel" aria-labelledby="explain-heading"><p className="section-kicker">Decision logic</p><h2 id="explain-heading">What this plan optimizes</h2>{optimized ? <><p>{largestRecommendation ? <><strong>{largestRecommendation.department} · {largestRecommendation.role}</strong> receives the largest displayed allocation because it has a projected staffing shortage, can arrive inside the planning horizon, and the submitted budget and recruiting capacity permit the allocation.</> : "No additional in-horizon hire improves the scenario under the submitted constraints."}</p>{optimized.unused_budget > 0 && <p>{currency.format(optimized.unused_budget)} remains unused because no additional in-horizon hire improves the objective under the submitted staffing targets, capacity, and lead times.</p>}<p className="model-limit">V1 minimizes total understaffed FTE-months. It does not model role criticality, revenue impact, skill scarcity, employee or candidate quality, or strategic priority weights.</p></> : <p>Run a scenario and optimize it to see a deterministic explanation based on the submitted assumptions and actual solver output.</p>}</section>
    </section>

    {optimized && <section className="recommendation-panel" aria-labelledby="recommendations-heading"><div className="panel-heading"><div><p className="section-kicker">Recommended hiring plan</p><h2 id="recommendations-heading">Starts and arrivals</h2></div><p className="solver-status">{optimized.solver}; primary {optimized.primary_status}, secondary {optimized.secondary_status}</p></div><p>Spend used {currency.format(optimized.planning_period_incremental_workforce_spend_used)} of {currency.format(optimized.submitted_budget)} · {currency.format(optimized.unused_budget)} unused</p>{optimized.recommendations.length === 0 ? <p>No optimized hiring starts.</p> : <table><thead><tr><th>Department</th><th>Role</th><th>Hires</th><th>Start month</th><th>Arrival month</th><th>Planning-period spend</th></tr></thead><tbody>{optimized.recommendations.map((item) => <tr key={`${item.role_id}-${item.decision_month}-${item.arrival_month}`}><td>{item.department}</td><td>{item.role}</td><td>{item.hires}</td><td>Month {item.decision_month}</td><td>Month {item.arrival_month}</td><td>{currency.format(item.planning_period_incremental_workforce_spend)}</td></tr>)}</tbody></table>}</section>}
  </main>;
}
