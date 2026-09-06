import { expect, Page, test } from "@playwright/test";

async function openDecisionLab(page: Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "What changed, where risk is building, and what to do next." })).toBeVisible();
  await page.getByRole("button", { name: "Decision Lab", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What does this fixed simulation show?" })).toBeVisible();
}

test("Flow A: Overview displays seeded metrics and opens Decision Lab", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "What changed, where risk is building, and what to do next." })).toBeVisible();
  const metrics = page.getByRole("region", { name: "Workforce key performance indicators" });
  await expect(metrics.getByText("160.0", { exact: true })).toBeVisible();
  await expect(metrics.getByText("117.6", { exact: true })).toBeVisible();
  await expect(page.getByRole("row", { name: /Sales 47\.5 10\.4 2\.5%/ })).toBeVisible();
  await page.getByRole("button", { name: "Model this in Decision Lab" }).click();
  await expect(page.getByRole("heading", { name: "What does this fixed simulation show?" })).toBeVisible();
});

test("Flow B: changed scenario compares, then reset restores persisted input", async ({ page }) => {
  await openDecisionLab(page);
  const attrition = page.getByLabel("Annual expected attrition");
  await attrition.fill("18");
  await page.getByRole("button", { name: "Run Scenario", exact: true }).click();
  await expect(page.getByText("Scenario active", { exact: true })).toBeVisible();
  const cards = page.locator(".summary-card");
  await expect(cards).toHaveCount(2);
  expect(await cards.nth(1).innerText()).not.toEqual(await cards.nth(0).innerText());
  await page.getByRole("button", { name: "Reset to Baseline" }).click();
  await expect(page.getByText("Scenario active", { exact: true })).toHaveCount(0);
  await expect(attrition).toHaveValue("12");
});

test("Flow C: valid optimization displays a safe optimal recommendation", async ({ page }) => {
  await openDecisionLab(page);
  await page.getByRole("button", { name: "Run Scenario", exact: true }).click();
  await expect(page.getByText("Scenario active", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Optimize Scenario", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Starts and arrivals" })).toBeVisible();
  await expect(page.getByText(/SCIP; primary OPTIMAL, secondary OPTIMAL/)).toBeVisible();
  await expect(page.getByText(/Spend used \$150,000 of \$150,000/)).toBeVisible();
});

test("Flow D: invalid input has an understandable error and no optimization", async ({ page }) => {
  await openDecisionLab(page);
  await page.getByLabel("Annual expected attrition").fill("100");
  await page.getByRole("button", { name: "Run Scenario", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("below 100%");
  await expect(page.getByRole("heading", { name: "Starts and arrivals" })).toHaveCount(0);
});

test("Flow E: mobile navigation keeps synthetic demo provenance visible", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/");
  await expect(page.getByText("· Synthetic demo data", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Overview", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Decision Lab", exact: true })).toBeVisible();
});
