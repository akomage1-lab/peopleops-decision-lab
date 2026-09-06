import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const organizationMonths = Array.from({ length: 6 }, (_, index) => ({
  month: `2026-0${index + 1}-01`, expected_fte: 160 - index, staffing_target: 170 + index, staffing_shortage: 10 + index
}));
const sdrProvenance = {
  role_id: 5, department_id: 2, department: "Sales", role: "Sales Development Representative",
  observation_date: "2025-12-01", starting_observed_fte: 14, annual_expected_attrition_rate: 0.12,
  staffing_targets: [18, 18, 19, 19, 20, 20], in_flight_hires: [0, 0, 0, 0, 0, 0]
};
const engineerProvenance = {
  role_id: 6, department_id: 3, department: "Engineering", role: "Software Engineer",
  observation_date: "2025-12-01", starting_observed_fte: 20, annual_expected_attrition_rate: 0.08,
  staffing_targets: [22, 22, 23, 23, 24, 24], in_flight_hires: [0, 0, 0, 0, 0, 0]
};
const roleMonth = {
  role_id: 5, department_id: 2, department: "Sales", role: "Sales Development Representative", month: "2026-01-01",
  expected_fte: 13.85, staffing_target: 18, staffing_shortage: 4.15
};
const baseline = {
  generated_at: "2026-01-01T00:00:00Z", model_version: "m1-baseline-forecast-v1", planning_horizon_months: 6,
  observation_date: "2025-12-01", role_provenance: [sdrProvenance, engineerProvenance],
  role_months: [{ ...roleMonth, expected_fte_before_attrition: 14, expected_attrition_loss: .15, in_flight_hires_arriving: 0, staffing_surplus: 0 }],
  department_months: organizationMonths.map((row) => ({ ...row, department_id: 2, department: "Sales" })),
  organization_months: organizationMonths, total_understaffed_fte_months: 117.61
};
const scenario = {
  generated_at: "2026-01-01T00:00:00Z", model_version: "m1-production-scenario-forecast-v1", observation_date: "2025-12-01", planning_horizon_months: 6,
  role_months: [{ ...roleMonth, expected_fte: 13.7, staffing_target: 20, staffing_shortage: 6.3 }],
  department_months: organizationMonths.map((row) => ({ ...row, department_id: 2, department: "Sales" })),
  organization_months: organizationMonths.map((row) => ({ ...row, expected_fte: row.expected_fte - 1, staffing_target: row.staffing_target + 1, staffing_shortage: row.staffing_shortage + 2 })),
  total_understaffed_fte_months: 131.24
};
const optimized = {
  generated_at: "2026-01-01T00:00:00Z", model_version: "m1-production-optimizer-v1", observation_date: "2025-12-01", planning_horizon_months: 6,
  submitted_budget: 150000, submitted_monthly_recruiting_capacity: [2, 2, 2, 2, 2, 2], solver: "SCIP", primary_status: "OPTIMAL", secondary_status: "OPTIMAL", optimization_duration_ms: 53,
  baseline_understaffed_fte_months: 131.24, baseline_role_months: scenario.role_months, baseline_department_months: scenario.department_months, baseline_organization_months: scenario.organization_months,
  optimized_understaffed_fte_months: 111.57, improvement_understaffed_fte_months: 19.67, planning_period_incremental_workforce_spend_used: 150000, unused_budget: 0,
  recommendations: [{ role_id: 5, department_id: 2, department: "Sales", role: "Sales Development Representative", hires: 2, decision_month: 1, arrival_month: 2, planning_period_incremental_workforce_spend: 75000 }],
  optimized_role_months: scenario.role_months, optimized_department_months: scenario.department_months, optimized_organization_months: scenario.organization_months
};
const sensitivity = {
  generated_at: "2026-01-01T00:00:01Z", model_version: "m1-production-optimizer-v1-m11-sensitivity-v1", submitted_budget: 150000, submitted_monthly_recruiting_capacity: [2, 2, 2, 2, 2, 2], sensitivity_execution_duration_ms: 95,
  budget_sensitivity: [
    { budget: 75000, optimized_understaffed_fte_months: 121.57, planning_period_incremental_workforce_spend_used: 75000, unused_budget: 0, total_optimizer_selected_hires: 1, primary_status: "OPTIMAL", secondary_status: "OPTIMAL", optimization_duration_ms: 10 },
    { budget: 112500, optimized_understaffed_fte_months: 115.57, planning_period_incremental_workforce_spend_used: 112500, unused_budget: 0, total_optimizer_selected_hires: 2, primary_status: "OPTIMAL", secondary_status: "OPTIMAL", optimization_duration_ms: 11 },
    { budget: 150000, optimized_understaffed_fte_months: 111.57, planning_period_incremental_workforce_spend_used: 150000, unused_budget: 0, total_optimizer_selected_hires: 2, primary_status: "OPTIMAL", secondary_status: "OPTIMAL", optimization_duration_ms: 12 },
    { budget: 187500, optimized_understaffed_fte_months: 109.57, planning_period_incremental_workforce_spend_used: 180000, unused_budget: 7500, total_optimizer_selected_hires: 3, primary_status: "OPTIMAL", secondary_status: "OPTIMAL", optimization_duration_ms: 13 }
  ],
  recruiting_capacity_sensitivity: [
    { monthly_recruiting_capacity: [1, 1, 1, 1, 1, 1], monthly_recruiting_capacity_delta: [-1, -1, -1, -1, -1, -1], optimized_understaffed_fte_months: 114.57, planning_period_incremental_workforce_spend_used: 150000, total_optimizer_selected_hires: 2, primary_status: "OPTIMAL", secondary_status: "OPTIMAL", optimization_duration_ms: 14 },
    { monthly_recruiting_capacity: [2, 2, 2, 2, 2, 2], monthly_recruiting_capacity_delta: [0, 0, 0, 0, 0, 0], optimized_understaffed_fte_months: 111.57, planning_period_incremental_workforce_spend_used: 150000, total_optimizer_selected_hires: 2, primary_status: "OPTIMAL", secondary_status: "OPTIMAL", optimization_duration_ms: 15 },
    { monthly_recruiting_capacity: [3, 3, 3, 3, 3, 3], monthly_recruiting_capacity_delta: [1, 1, 1, 1, 1, 1], optimized_understaffed_fte_months: 106.57, planning_period_incremental_workforce_spend_used: 150000, total_optimizer_selected_hires: 3, primary_status: "OPTIMAL", secondary_status: "OPTIMAL", optimization_duration_ms: 16 }
  ]
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function mockFetch(...responses: Response[]) {
  const fetchMock = vi.fn();
  responses.forEach((response) => fetchMock.mockResolvedValueOnce(response));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("M6 Decision Lab", () => {
  it("keeps the initial loading surface accessible while the baseline request is pending", async () => {
    let resolveBaseline: (response: Response) => void = () => undefined;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise<Response>((resolve) => { resolveBaseline = resolve; })));
    const { container } = render(<App />);
    expect(screen.getByText("Loading the persisted synthetic demo baseline…")).toBeInTheDocument();
    expect(container.querySelector(".loading-surface .inline-spinner")).toBeInTheDocument();
    expect(container.querySelector("main")?.getAttribute("aria-busy")).toBe("true");
    resolveBaseline(jsonResponse(baseline));
    expect(await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" })).toBeInTheDocument();
  });

  it("loads the real baseline presentation", async () => {
    mockFetch(jsonResponse(baseline));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" })).toBeInTheDocument();
    expect(screen.getAllByText("117.6")).toHaveLength(2);
    expect(screen.getByLabelText("Annual expected attrition")).toHaveValue(12);
    expect(screen.getByText(/fixed Jan 2026–Jun 2026 synthetic demo forecast/)).toBeInTheDocument();
    expect(screen.getByText(/FTE means full-time equivalent/)).toBeInTheDocument();
    expect(screen.getByText(/being 1 FTE below the staffing target for one month/)).toBeInTheDocument();
    expect(screen.getByText(/This is a forecast.*not current staffing data/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Role-specific assumptions" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Company-wide optimizer constraints" })).toBeInTheDocument();
    expect(screen.getByText("These limits apply to the optimized hiring plan across all roles, not only the selected role above.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Company-wide plan comparison/ })).toBeInTheDocument();
    expect(screen.getAllByText("Company-wide baseline forecast").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Company-wide scenario").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Company-wide optimized plan").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Company-wide staffing trajectory" })).toBeInTheDocument();
    expect(screen.getByText(/Estimated percentage of this role expected to leave over a year/)).toBeInTheDocument();
    expect(screen.getByText(/staffing capacity you want this role to reach in each month/)).toBeInTheDocument();
    expect(screen.getByLabelText("Company-wide optimizer budget (USD)")).toHaveValue(150000);
    expect(screen.getByText("USD")).toBeInTheDocument();
    expect(screen.getByText(/Maximum modeled in-horizon loaded workforce cost. Each selected hire costs its role’s monthly loaded cost for every month from arrival through Jun 2026, so a later arrival costs fewer in-horizon months/)).toBeInTheDocument();
    expect(screen.getByText(/Maximum optimizer-selected starts across all roles in each month/)).toBeInTheDocument();
    expect(screen.getByText(/The optimizer chooses hire starts that minimize company-wide understaffed FTE-months while respecting budget, capacity, and role lead times/)).toBeInTheDocument();
    expect(screen.queryByText(/salary|benefits|recruiting fees|total compensation/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/next 6 months/i)).not.toBeInTheDocument();
  });

  it("runs a changed transient scenario and displays the comparison", async () => {
    const fetchMock = mockFetch(jsonResponse(baseline), jsonResponse(scenario));
    render(<App />);
    await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" });
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "18" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    expect(await screen.findByText("Scenario active")).toBeInTheDocument();
    expect(screen.getByText("131.2")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/api/workforce/scenario/forecast", expect.objectContaining({ body: expect.stringContaining("0.18") }));
  });

  it("shows optimizer recommendations after the scenario run", async () => {
    const fetchMock = mockFetch(jsonResponse(baseline), jsonResponse(scenario), jsonResponse(optimized));
    render(<App />);
    await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    await screen.findByText("Scenario active");
    fireEvent.click(screen.getByRole("button", { name: "Optimize Scenario" }));
    expect(await screen.findByRole("heading", { name: "Recommended hire starts and arrivals" })).toBeInTheDocument();
    expect(screen.getAllByText("Sales Development Representative").length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenLastCalledWith("/api/workforce/scenario/optimize", expect.anything());
    expect(screen.getByText("Decision audit")).toBeInTheDocument();
    expect(screen.getByText("Goal")).toBeInTheDocument();
    expect(screen.getByText("Constraints used")).toBeInTheDocument();
    expect(screen.getByText("Result")).toBeInTheDocument();
    expect(screen.getByText(/131.2 → 111.6 company-wide total understaffing/)).toBeInTheDocument();
    expect(screen.getByText(/Minimize company-wide total understaffed FTE-months/)).toBeInTheDocument();
    expect(screen.getAllByText(/Optimization status: Optimal/).length).toBeGreaterThan(0);
    expect(screen.getByText(/no feasible plan with lower total understaffing/)).toBeInTheDocument();
    expect(screen.getByText(/Among plans tied on understaffing/)).toBeInTheDocument();
    expect(screen.getByText(/globally optimized combination/)).toBeInTheDocument();
    expect(screen.getByText(/not as the organization’s final hiring-priority decision/)).toBeInTheDocument();
    expect(screen.queryByText(/receives the largest displayed allocation because/)).not.toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Jan 2026" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Feb 2026" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze constraint sensitivity" })).toBeInTheDocument();
  });

  it("runs bounded sensitivity with the current transient constraints and preserves an optimization on failure", async () => {
    const fetchMock = mockFetch(jsonResponse(baseline), jsonResponse(scenario), jsonResponse(optimized), jsonResponse(sensitivity));
    render(<App />);
    await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" });
    expect(screen.queryByRole("button", { name: "Analyze constraint sensitivity" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "18" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    await screen.findByText("Scenario active");
    fireEvent.click(screen.getByRole("button", { name: "Optimize Scenario" }));
    await screen.findByRole("button", { name: "Analyze constraint sensitivity" });
    fireEvent.click(screen.getByRole("button", { name: "Analyze constraint sensitivity" }));
    expect(await screen.findByRole("heading", { name: "Budget frontier" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recruiting-capacity sensitivity" })).toBeInTheDocument();
    expect(screen.getByText("Submitted budget")).toBeInTheDocument();
    expect(screen.getByText("Submitted")).toBeInTheDocument();
    expect(screen.getByText(/reduces optimized understaffing by 5.0 FTE-months.*reduces it by 2.0 FTE-months/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/api/workforce/scenario/sensitivity", expect.objectContaining({ body: expect.stringContaining("0.18") }));
    const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect(JSON.parse(String(lastCall[1]?.body))).toMatchObject({ planning_period_incremental_workforce_budget: 150000, monthly_recruiting_capacity: [2, 2, 2, 2, 2, 2] });
    fireEvent.change(screen.getByLabelText("Company-wide optimizer budget (USD)"), { target: { value: "160000" } });
    expect(screen.queryByRole("heading", { name: "Constraint sensitivity" })).not.toBeInTheDocument();
  });

  it("keeps the successful optimized plan visible if sensitivity fails", async () => {
    mockFetch(jsonResponse(baseline), jsonResponse(scenario), jsonResponse(optimized), jsonResponse({ detail: "Sensitivity service unavailable." }, 503));
    render(<App />);
    await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    await screen.findByText("Scenario active");
    fireEvent.click(screen.getByRole("button", { name: "Optimize Scenario" }));
    await screen.findByRole("heading", { name: "Recommended hire starts and arrivals" });
    fireEvent.click(screen.getByRole("button", { name: "Analyze constraint sensitivity" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Sensitivity service unavailable.");
    expect(screen.getByRole("heading", { name: "Recommended hire starts and arrivals" })).toBeInTheDocument();
  });

  it("resets changed inputs to the persisted baseline assumptions", async () => {
    mockFetch(jsonResponse(baseline));
    render(<App />);
    await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" });
    const attrition = screen.getByLabelText("Annual expected attrition");
    fireEvent.change(attrition, { target: { value: "18" } });
    expect(attrition).toHaveValue(18);
    expect(screen.getByText("Scenario includes edits to 1 role:")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reset to Baseline" }));
    expect(screen.getByLabelText("Annual expected attrition")).toHaveValue(12);
    expect(screen.getByLabelText("Company-wide optimizer budget (USD)")).toHaveValue(150000);
    expect(screen.queryByText(/Scenario includes edits to/)).not.toBeInTheDocument();
  });

  it("shows only actual active role edits and removes a reverted no-op", async () => {
    mockFetch(jsonResponse(baseline));
    render(<App />);
    await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" });
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "18" } });
    fireEvent.change(screen.getByLabelText("Role to edit"), { target: { value: "6" } });
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "10" } });
    expect(screen.getByText("Scenario includes edits to 2 roles:")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem").map((item) => item.textContent)).toEqual(expect.arrayContaining(["Sales · Sales Development Representative", "Engineering · Software Engineer"]));
    fireEvent.change(screen.getByLabelText("Role to edit"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "12" } });
    expect(screen.getByText("Scenario includes edits to 1 role:")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem").map((item) => item.textContent)).not.toContain("Sales · Sales Development Representative");
  });

  it("shows useful validation and API error states", async () => {
    mockFetch(jsonResponse(baseline), jsonResponse({ detail: "Scenario service unavailable." }, 503));
    render(<App />);
    await screen.findByRole("heading", { name: "Baseline forecast: the unchanged demo plan" });
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "100" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("below 100%");
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "18" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Scenario service unavailable."));
  });
});
