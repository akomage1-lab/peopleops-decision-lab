import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const scenario = {
  id: 1,
  name: "M2 Seeded Workforce Plan",
  planning_horizon_months: 6,
  planning_period_incremental_workforce_budget: 170000
};

const result = {
  scenario_id: 1,
  available_budget: 100000,
  baseline_understaffed_fte_months: 10,
  optimized_understaffed_fte_months: 4,
  improvement_understaffed_fte_months: 6,
  incremental_workforce_spend_used: 90000,
  recommendations: [{ department: "Sales", role: "Account Executive", decision_month: 1, arrival_month: 1, hires: 1, incremental_workforce_spend: 90000 }],
  solver_status: { solver: "SCIP", primary: "OPTIMAL", secondary: "OPTIMAL" }
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("M2 walking-skeleton page", () => {
  it("renders the fetched scenario and shows a successful optimization", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse(scenario)).mockResolvedValueOnce(jsonResponse(result));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(await screen.findByRole("heading", { name: scenario.name })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Planning-period incremental workforce budget"), { target: { value: "100000" } });
    fireEvent.click(screen.getByRole("button", { name: "Optimize Plan" }));

    expect(await screen.findByText("Recommended hiring starts")).toBeInTheDocument();
    expect(screen.getByText("Sales / Account Executive")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/api/scenarios/1/optimize", expect.objectContaining({ body: JSON.stringify({ planning_period_incremental_workforce_budget: 100000 }) }));
  });

  it("shows an obvious API error state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse(scenario)).mockResolvedValueOnce(jsonResponse({ detail: "Optimizer unavailable." }, 503)));
    render(<App />);
    await screen.findByRole("heading", { name: scenario.name });
    fireEvent.click(screen.getByRole("button", { name: "Optimize Plan" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Optimizer unavailable."));
  });
});
