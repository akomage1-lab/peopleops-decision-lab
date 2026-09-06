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
  it("loads the real baseline presentation", async () => {
    mockFetch(jsonResponse(baseline));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "What does this fixed simulation show?" })).toBeInTheDocument();
    expect(screen.getAllByText("117.6")).toHaveLength(2);
    expect(screen.getByLabelText("Annual expected attrition")).toHaveValue(12);
    expect(screen.getByText(/Jan 2026–Jun 2026 demo planning horizon/)).toBeInTheDocument();
    expect(screen.getByText(/1 understaffed FTE-month means being short one full-time employee for one month/)).toBeInTheDocument();
    expect(screen.queryByText(/next 6 months/i)).not.toBeInTheDocument();
  });

  it("runs a changed transient scenario and displays the comparison", async () => {
    const fetchMock = mockFetch(jsonResponse(baseline), jsonResponse(scenario));
    render(<App />);
    await screen.findByRole("heading", { name: "What does this fixed simulation show?" });
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "18" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    expect(await screen.findByText("Scenario active")).toBeInTheDocument();
    expect(screen.getByText("131.2")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/api/workforce/scenario/forecast", expect.objectContaining({ body: expect.stringContaining("0.18") }));
  });

  it("shows optimizer recommendations after the scenario run", async () => {
    const fetchMock = mockFetch(jsonResponse(baseline), jsonResponse(scenario), jsonResponse(optimized));
    render(<App />);
    await screen.findByRole("heading", { name: "What does this fixed simulation show?" });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    await screen.findByText("Scenario active");
    fireEvent.click(screen.getByRole("button", { name: "Optimize Scenario" }));
    expect(await screen.findByRole("heading", { name: "Starts and arrivals" })).toBeInTheDocument();
    expect(screen.getAllByText("Sales Development Representative").length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenLastCalledWith("/api/workforce/scenario/optimize", expect.anything());
    expect(screen.getByText(/feasible combinations of integer hire starts/)).toBeInTheDocument();
    expect(screen.getByText(/globally optimized combination/)).toBeInTheDocument();
    expect(screen.getByText(/not a business-priority ranking/)).toBeInTheDocument();
    expect(screen.queryByText(/receives the largest displayed allocation because/)).not.toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Jan 2026" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Feb 2026" })).toBeInTheDocument();
  });

  it("resets changed inputs to the persisted baseline assumptions", async () => {
    mockFetch(jsonResponse(baseline));
    render(<App />);
    await screen.findByRole("heading", { name: "What does this fixed simulation show?" });
    const attrition = screen.getByLabelText("Annual expected attrition");
    fireEvent.change(attrition, { target: { value: "18" } });
    expect(attrition).toHaveValue(18);
    expect(screen.getByText("Scenario includes edits to 1 role:")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reset to Baseline" }));
    expect(screen.getByLabelText("Annual expected attrition")).toHaveValue(12);
    expect(screen.getByLabelText("Planning-period incremental workforce budget")).toHaveValue(150000);
    expect(screen.queryByText(/Scenario includes edits to/)).not.toBeInTheDocument();
  });

  it("shows only actual active role edits and removes a reverted no-op", async () => {
    mockFetch(jsonResponse(baseline));
    render(<App />);
    await screen.findByRole("heading", { name: "What does this fixed simulation show?" });
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
    await screen.findByRole("heading", { name: "What does this fixed simulation show?" });
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "100" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("below 100%");
    fireEvent.change(screen.getByLabelText("Annual expected attrition"), { target: { value: "18" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Scenario" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Scenario service unavailable."));
  });
});
