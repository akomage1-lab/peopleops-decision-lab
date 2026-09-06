import { useEffect, useState } from "react";
import {
  OverviewForecastMonth,
  OverviewHistoricalTrend,
  WorkforceOverview,
  fetchWorkforceOverview
} from "./api";
import "./styles.css";

const oneDecimal = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const wholeNumber = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const month = (value: string, withYear = false) => new Intl.DateTimeFormat("en-US", withYear ? { month: "short", year: "numeric" } : { month: "short" }).format(new Date(`${value}T12:00:00`));
const percent = (value: number | null) => value === null ? "Not available" : `${(value * 100).toFixed(1)}%`;

function forecastPoints(months: OverviewForecastMonth[], metric: "expected_fte" | "staffing_target", max: number) {
  return months.map((row, index) => `${24 + index * 58},${126 - (row[metric] / max) * 104}`).join(" ");
}

function observedPoints(points: OverviewHistoricalTrend[], max: number) {
  const step = points.length > 1 ? 296 / (points.length - 1) : 0;
  return points.map((row, index) => `${24 + index * step},${126 - (row.total_fte / max) * 104}`).join(" ");
}

function ForecastChart({ months }: { months: OverviewForecastMonth[] }) {
  const max = Math.max(...months.map((item) => Math.max(item.expected_fte, item.staffing_target)), 1) * 1.04;
  return <figure className="chart-card overview-chart" aria-labelledby="overview-forecast-heading">
    <figcaption><p className="section-kicker">Forward-looking baseline</p><h2 id="overview-forecast-heading">Six-month staffing trajectory</h2><p>Baseline expected FTE versus staffing target. This is a forecast, not observed history.</p></figcaption>
    <svg viewBox="0 0 340 154" role="img" aria-label="Six-month baseline workforce forecast">
      <line x1="24" y1="126" x2="320" y2="126" className="chart-axis" />
      <line x1="24" y1="22" x2="24" y2="126" className="chart-axis" />
      <polyline points={forecastPoints(months, "staffing_target", max)} className="chart-line target" />
      <polyline points={forecastPoints(months, "expected_fte", max)} className="chart-line baseline" />
      {months.map((row, index) => <text key={row.month} x={19 + index * 58} y="145" className="chart-label">{month(row.month)}</text>)}
    </svg>
    <div className="legend"><span><i className="legend-target" />Target</span><span><i className="legend-baseline" />Baseline expected FTE</span></div>
  </figure>;
}

function ObservedTrend({ history }: { history: OverviewHistoricalTrend[] }) {
  const max = Math.max(...history.map((item) => item.total_fte), 1) * 1.03;
  const labels = [history[0], history[Math.floor(history.length / 2)], history[history.length - 1]].filter(Boolean);
  return <figure className="chart-card overview-chart" aria-labelledby="observed-history-heading">
    <figcaption><p className="section-kicker">Historical context</p><h2 id="observed-history-heading">Observed workforce trend</h2><p>Observed organization FTE; not a forecast.</p></figcaption>
    <svg viewBox="0 0 340 154" role="img" aria-label="Observed workforce FTE history">
      <line x1="24" y1="126" x2="320" y2="126" className="chart-axis" />
      <line x1="24" y1="22" x2="24" y2="126" className="chart-axis" />
      <polyline points={observedPoints(history, max)} className="chart-line observed" />
      {labels.map((row) => <text key={row.month} x={24 + (history.indexOf(row) * (history.length > 1 ? 296 / (history.length - 1) : 0)) - 7} y="145" className="chart-label">{month(row.month)}</text>)}
    </svg>
    <div className="legend"><span><i className="legend-observed" />Observed FTE</span></div>
  </figure>;
}

export default function Overview({ onOpenDecisionLab }: { onOpenDecisionLab: () => void }) {
  const [overview, setOverview] = useState<WorkforceOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchWorkforceOverview()
      .then(setOverview)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Unable to load workforce analytics."));
  }, []);

  if (error) return <main className="app-shell"><p className="error" role="alert">{error}</p></main>;
  if (!overview) return <main className="app-shell"><p className="loading">Loading workforce analytics from the production baseline…</p></main>;

  const recentPeriod = `${month(overview.recent_historical_start_month, true)}–${month(overview.recent_historical_end_month, true)}`;
  return <main className="app-shell overview-shell">
    <header className="hero overview-hero">
      <p className="eyebrow">Executive workforce overview</p>
      <h1>What changed, where risk is building, and what to do next.</h1>
      <p>Observed through {month(overview.observation_date, true)}. The forward view is the persisted six-month baseline from {month(overview.next_planning_month, true)}.</p>
    </header>

    <section className="kpi-grid" aria-label="Workforce key performance indicators">
      <article className="kpi-card"><p>Current observed FTE</p><strong>{oneDecimal.format(overview.current_total_fte)}</strong><span>as of {month(overview.observation_date, true)}</span></article>
      <article className="kpi-card"><p>Next planning target</p><strong>{oneDecimal.format(overview.next_planning_target)}</strong><span>{month(overview.next_planning_month, true)}</span></article>
      <article className="kpi-card"><p>Current staffing gap</p><strong>{oneDecimal.format(overview.current_staffing_gap)}</strong><span>FTE to next target</span></article>
      <article className="kpi-card emphasis"><p>Six-month understaffing</p><strong>{oneDecimal.format(overview.six_month_understaffed_fte_months)}</strong><span>baseline FTE-months</span></article>
    </section>

    <section className="overview-grid">
      <ForecastChart months={overview.forecast_months} />
      <section className="insight-card" aria-labelledby="operating-signals-heading">
        <p className="section-kicker">Observed operating signals</p><h2 id="operating-signals-heading">Recent flow and hiring evidence</h2>
        <dl className="signal-list">
          <div><dt>Observed hires ({recentPeriod})</dt><dd>{wholeNumber.format(overview.recent_hires)}</dd></div>
          <div><dt>Observed exits ({recentPeriod})</dt><dd>{wholeNumber.format(overview.recent_exits)}</dd></div>
          <div><dt>Observed attrition ({recentPeriod})</dt><dd>{percent(overview.recent_attrition_rate)}</dd></div>
          <div><dt>Median completed-cycle time-to-fill</dt><dd>{overview.organization_median_time_to_fill_days === null ? "Not available" : `${wholeNumber.format(overview.organization_median_time_to_fill_days)} days`}</dd></div>
        </dl>
        <p className="model-limit">Attrition and time-to-fill are historical measurements. They are not a causal diagnosis or a recommendation by themselves.</p>
      </section>
    </section>

    <section className="overview-grid lower-overview-grid">
      <section className="table-panel" aria-labelledby="future-risk-heading">
        <p className="section-kicker">Forward-looking risk</p><h2 id="future-risk-heading">Departments concentrating baseline understaffing</h2>
        <p className="helper">Ranked by cumulative six-month baseline understaffed FTE-months.</p>
        <table><thead><tr><th>Department</th><th>6-mo risk</th><th>Month 6 gap</th><th>Recent attrition</th></tr></thead><tbody>{overview.department_risks.map((item) => <tr key={item.department}><td>{item.department}</td><td><span className="gap-value">{oneDecimal.format(item.total_understaffed_fte_months)}</span></td><td>{oneDecimal.format(item.end_of_horizon_shortage)}</td><td>{percent(item.recent_attrition_rate)}</td></tr>)}</tbody></table>
        <button type="button" className="overview-cta" onClick={onOpenDecisionLab}>Model this in Decision Lab</button>
      </section>
      <section className="table-panel" aria-labelledby="lead-time-heading">
        <p className="section-kicker">Historical hiring friction</p><h2 id="lead-time-heading">Slowest completed hiring cycles</h2>
        <p className="helper">Ranked by median days; counts show the observed evidence behind each measure.</p>
        <table><thead><tr><th>Department · role</th><th>Median days</th><th>Cycles</th></tr></thead><tbody>{overview.slowest_filling_roles.map((item) => <tr key={`${item.department}-${item.role}`}><td>{item.department} · {item.role}</td><td>{item.median_days === null ? "Not available" : wholeNumber.format(item.median_days)}</td><td>{item.completed_cycles}</td></tr>)}</tbody></table>
      </section>
    </section>

    <section className="overview-grid observed-grid"><ObservedTrend history={overview.historical_trend} /><section className="explain-panel" aria-labelledby="decision-lab-heading"><p className="section-kicker">Decision path</p><h2 id="decision-lab-heading">Turn the baseline into a constrained plan</h2><p>Decision Lab starts from the same persisted baseline. Adjust transient staffing assumptions, planning-period incremental workforce budget, and monthly recruiting capacity; then compare the resulting optimized plan.</p><button type="button" onClick={onOpenDecisionLab}>Open Decision Lab</button><p className="model-limit">The optimizer minimizes understaffed FTE-months. It does not infer business priority, revenue impact, or role criticality.</p></section></section>
  </main>;
}
