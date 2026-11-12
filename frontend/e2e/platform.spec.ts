import { test, expect } from "@playwright/test";

test("login, datasets, evaluation, real progress, traces, comparison, quality gates and mobile", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("Email address").fill("demo@agentbench.local");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.AB_DEMO_PASSWORD || "demo-agentbench-local-2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Evaluation overview" }),
  ).toBeVisible();
  await expect(page.locator(".recharts-surface").first()).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/overview.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Datasets", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Evaluation datasets" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /ci-smoke/ }).click();
  await expect(page.getByText("finance-001", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/datasets.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Run evaluation", exact: true })
    .click();
  await page
    .getByLabel("Evaluation agent", { exact: true })
    .selectOption({ label: "Financial Research" });
  await page
    .getByLabel("Agent version", { exact: true })
    .selectOption({ label: "v1 · baseline" });
  await page
    .getByLabel("Evaluation dataset", { exact: true })
    .selectOption({ label: "ci-smoke" });
  await page
    .getByRole("button", { name: "Start evaluation", exact: true })
    .click();
  await expect(page.getByText("12 / 12 cases completed")).toBeVisible({
    timeout: 120000,
  });
  await expect(
    page.getByText("Quality gate: PASS", { exact: true }),
  ).toBeVisible({ timeout: 120000 });
  await page.screenshot({
    path: "../docs/screenshots/results.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Explore traces", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Agent trace explorer" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Execution trajectory" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /ToolCalled/ })
    .first()
    .click();
  await expect(page.getByRole("heading", { name: "ToolCalled" })).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/trace.png",
    fullPage: true,
  });
  const operationOption = await page
    .getByLabel("Evaluation run")
    .locator("option")
    .filter({ hasText: "Financial Operations v1 · financial-operations" })
    .first()
    .getAttribute("value");
  await page.getByLabel("Evaluation run").selectOption(operationOption!);
  await page.getByLabel("Trace test case").selectOption("ops-013");
  await expect(
    page.getByRole("button", { name: /HumanApprovalRequested/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /HumanApprovalReceived/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/approval-resume.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Regression comparison", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Regression comparison" }),
  ).toBeVisible();
  const baseline = page.getByLabel("Baseline run"),
    candidate = page.getByLabel("Candidate run");
  const baselineOption = await baseline
    .locator("option")
    .filter({ hasText: "v1 · financial-research" })
    .first()
    .getAttribute("value");
  const candidateOption = await candidate
    .locator("option")
    .filter({ hasText: "v2-faulty · financial-research" })
    .first()
    .getAttribute("value");
  expect(baselineOption).toBeTruthy();
  expect(candidateOption).toBeTruthy();
  await baseline.selectOption(baselineOption!);
  await candidate.selectOption(candidateOption!);
  await page.getByRole("button", { name: "Compare runs" }).click();
  await expect(
    page.getByRole("heading", { name: "Statistical assessment" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/comparison.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Quality gates", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "CI/CD quality gates" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
