export interface Scenario {
  id: number;
  name: string;
  planning_horizon_months: number;
  planning_period_incremental_workforce_budget: number;
}

export interface Recommendation {
  department: string;
  role: string;
  decision_month: number;
  arrival_month: number;
  hires: number;
  incremental_workforce_spend: number;
}

export interface OptimizationResult {
  scenario_id: number;
  available_budget: number;
  baseline_understaffed_fte_months: number;
  optimized_understaffed_fte_months: number;
  improvement_understaffed_fte_months: number;
  incremental_workforce_spend_used: number;
  recommendations: Recommendation[];
  solver_status: { solver: string; primary: string; secondary: string };
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export function fetchScenario(): Promise<Scenario> {
  return requestJson<Scenario>("/api/scenarios/1");
}

export function optimizePlan(budget: number): Promise<OptimizationResult> {
  return requestJson<OptimizationResult>("/api/scenarios/1/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ planning_period_incremental_workforce_budget: budget })
  });
}
