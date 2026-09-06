export interface RoleProvenance {
  role_id: number;
  department_id: number;
  department: string;
  role: string;
  observation_date: string;
  starting_observed_fte: number;
  annual_expected_attrition_rate: number;
  staffing_targets: number[];
  in_flight_hires: number[];
}

export interface RoleMonth {
  role_id: number;
  department_id: number;
  department: string;
  role: string;
  month: string;
  expected_fte: number;
  staffing_target: number;
  staffing_shortage: number;
}

export interface DepartmentMonth {
  department_id: number;
  department: string;
  month: string;
  expected_fte: number;
  staffing_target: number;
  staffing_shortage: number;
}

export interface OrganizationMonth {
  month: string;
  expected_fte: number;
  staffing_target: number;
  staffing_shortage: number;
}

export interface ProductionForecast {
  generated_at: string;
  model_version: string;
  planning_horizon_months: number;
  observation_date: string;
  role_provenance: RoleProvenance[];
  role_months: Array<RoleMonth & {
    expected_fte_before_attrition: number;
    expected_attrition_loss: number;
    in_flight_hires_arriving: number;
    staffing_surplus: number;
  }>;
  department_months: DepartmentMonth[];
  organization_months: OrganizationMonth[];
  total_understaffed_fte_months: number;
}

export interface OverviewForecastMonth {
  month: string;
  expected_fte: number;
  staffing_target: number;
  staffing_shortage: number;
}

export interface OverviewHistoricalTrend {
  month: string;
  total_fte: number;
  hires: number;
  exits: number;
}

export interface OverviewDepartmentRisk {
  department: string;
  current_fte: number;
  next_planning_target: number;
  current_staffing_gap: number;
  total_understaffed_fte_months: number;
  end_of_horizon_shortage: number;
  recent_attrition_rate: number | null;
  recent_exits: number;
  recent_hires: number;
}

export interface OverviewHiringLeadTime {
  department: string;
  role: string;
  completed_cycles: number;
  average_days: number | null;
  median_days: number | null;
}

export interface WorkforceOverview {
  generated_at: string;
  observation_date: string;
  next_planning_month: string;
  recent_historical_start_month: string;
  recent_historical_end_month: string;
  current_total_fte: number;
  next_planning_target: number;
  current_staffing_gap: number;
  six_month_understaffed_fte_months: number;
  recent_hires: number;
  recent_exits: number;
  recent_attrition_rate: number | null;
  organization_median_time_to_fill_days: number | null;
  forecast_months: OverviewForecastMonth[];
  historical_trend: OverviewHistoricalTrend[];
  department_risks: OverviewDepartmentRisk[];
  slowest_filling_roles: OverviewHiringLeadTime[];
}

export interface ScenarioRoleOverride {
  role_id: number;
  annual_expected_attrition_rate: number;
  staffing_targets: number[];
}

export interface ScenarioForecast {
  generated_at: string;
  model_version: string;
  observation_date: string;
  planning_horizon_months: number;
  role_months: RoleMonth[];
  department_months: DepartmentMonth[];
  organization_months: OrganizationMonth[];
  total_understaffed_fte_months: number;
}

export interface Recommendation {
  role_id: number;
  department_id: number;
  department: string;
  role: string;
  hires: number;
  decision_month: number;
  arrival_month: number;
  planning_period_incremental_workforce_spend: number;
}

export interface ProductionOptimizationResult {
  generated_at: string;
  model_version: string;
  observation_date: string;
  planning_horizon_months: number;
  submitted_budget: number;
  submitted_monthly_recruiting_capacity: number[];
  solver: string;
  primary_status: string;
  secondary_status: string;
  optimization_duration_ms: number;
  baseline_understaffed_fte_months: number;
  baseline_role_months: RoleMonth[];
  baseline_department_months: DepartmentMonth[];
  baseline_organization_months: OrganizationMonth[];
  optimized_understaffed_fte_months: number;
  improvement_understaffed_fte_months: number;
  planning_period_incremental_workforce_spend_used: number;
  unused_budget: number;
  recommendations: Recommendation[];
  optimized_role_months: RoleMonth[];
  optimized_department_months: DepartmentMonth[];
  optimized_organization_months: OrganizationMonth[];
}

export interface ScenarioOptimizationRequest {
  planning_period_incremental_workforce_budget: number;
  monthly_recruiting_capacity: number[];
  role_overrides: ScenarioRoleOverride[];
}

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE_URL = configuredApiBaseUrl ? configuredApiBaseUrl.replace(/\/+$/, "") : "";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export function fetchProductionForecast(): Promise<ProductionForecast> {
  return requestJson<ProductionForecast>("/api/workforce/forecast");
}

export function fetchWorkforceOverview(): Promise<WorkforceOverview> {
  return requestJson<WorkforceOverview>("/api/workforce/overview");
}

export function forecastScenario(roleOverrides: ScenarioRoleOverride[]): Promise<ScenarioForecast> {
  return requestJson<ScenarioForecast>("/api/workforce/scenario/forecast", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role_overrides: roleOverrides })
  });
}

export function optimizeScenario(request: ScenarioOptimizationRequest): Promise<ProductionOptimizationResult> {
  return requestJson<ProductionOptimizationResult>("/api/workforce/scenario/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  });
}
