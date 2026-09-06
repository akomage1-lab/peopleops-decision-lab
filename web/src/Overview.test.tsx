import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Overview from "./Overview";
import ProductApp from "./ProductApp";

vi.mock("./App", () => ({ default: () => <h1>Decision Lab loaded</h1> }));

const overview = {
  generated_at: "2026-01-01T00:00:00Z", observation_date: "2025-12-01", next_planning_month: "2026-01-01",
  recent_historical_start_month: "2025-10-01", recent_historical_end_month: "2025-12-01",
  current_total_fte: 160, next_planning_target: 170.5, current_staffing_gap: 10.5,
  six_month_understaffed_fte_months: 117.6104, recent_hires: 1, recent_exits: 7, recent_attrition_rate: 0.04312,
  organization_median_time_to_fill_days: 60,
  forecast_months: Array.from({ length: 6 }, (_, index) => ({ month: `2026-0${index + 1}-01`, expected_fte: 160 - index, staffing_target: 170 + index, staffing_shortage: 10 + index })),
  historical_trend: Array.from({ length: 12 }, (_, index) => ({ month: `2025-${String(index + 1).padStart(2, "0")}-01`, total_fte: 150 + index, hires: 1, exits: 0 })),
  department_risks: [
    { department: "Sales", current_fte: 39, next_planning_target: 44, current_staffing_gap: 5, total_understaffed_fte_months: 47.5, end_of_horizon_shortage: 10.4, recent_attrition_rate: 0.025, recent_exits: 1, recent_hires: 0 },
    { department: "Customer Support", current_fte: 28, next_planning_target: 30, current_staffing_gap: 2, total_understaffed_fte_months: 23.3, end_of_horizon_shortage: 6.8, recent_attrition_rate: null, recent_exits: 5, recent_hires: 1 }
  ],
  slowest_filling_roles: [
    { department: "Sales", role: "Account Executive", completed_cycles: 3, average_days: 105, median_days: 105 }
  ]
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("M7 executive overview", () => {
  it("renders server-provided executive KPIs, forecast, risk, and historical evidence", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(overview)));
    render(<Overview onOpenDecisionLab={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Plan staffing shortfalls before they become hiring gaps." })).toBeInTheDocument();
    expect(screen.getByText("117.6")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Synthetic demo planning workforce forecast" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Observed workforce FTE history" })).toBeInTheDocument();
    expect(screen.getByText(/fixed baseline planning forecast covers/)).toBeInTheDocument();
    expect(screen.getByText(/Find where staffing is projected to fall short/)).toBeInTheDocument();
    expect(screen.getByText(/FTE means full-time equivalent/)).toBeInTheDocument();
    expect(screen.getByText(/being 1 FTE below the staffing target for one month/)).toBeInTheDocument();
    expect(screen.getByText(/Baseline planning forecast/)).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Total understaffing (FTE-months)" })).toBeInTheDocument();
    expect(screen.getByText("Sales")).toBeInTheDocument();
    expect(screen.getByText("Sales · Account Executive")).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThan(0);
  });

  it("uses the explicit path to open Decision Lab", async () => {
    const onOpenDecisionLab = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(overview)));
    render(<Overview onOpenDecisionLab={onOpenDecisionLab} />);

    await screen.findByRole("heading", { name: "Turn the forecast into a constrained hiring plan" });
    fireEvent.click(screen.getByRole("button", { name: "Open Decision Lab" }));
    expect(onOpenDecisionLab).toHaveBeenCalledOnce();
  });

  it("switches product navigation from Overview to Decision Lab", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(overview)));
    render(<ProductApp />);

    await screen.findByRole("heading", { name: "Plan staffing shortfalls before they become hiring gaps." });
    fireEvent.click(screen.getByRole("button", { name: "Decision Lab" }));
    expect(screen.getByRole("heading", { name: "Decision Lab loaded" })).toBeInTheDocument();
    expect(screen.getByText("Portfolio demo — all company and workforce data shown here are synthetic.")).toBeInTheDocument();
  });

  it("renders a useful API failure state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Overview unavailable." }, 503)));
    render(<Overview onOpenDecisionLab={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Overview unavailable.");
  });
});
