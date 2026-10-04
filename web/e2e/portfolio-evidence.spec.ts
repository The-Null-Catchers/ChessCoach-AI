import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const enabled = process.env.PORTFOLIO_EVIDENCE === "true";
const email = process.env.PORTFOLIO_DEMO_EMAIL ?? "";
const password = process.env.PORTFOLIO_DEMO_PASSWORD ?? "";
const evidenceDir = resolve(process.cwd(), "portfolio-evidence");

async function settle(page: import("@playwright/test").Page) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForLoadState("networkidle").catch(() => undefined);
}

async function capture(page: import("@playwright/test").Page, name: string) {
  await settle(page);
  await page.screenshot({ path: resolve(evidenceDir, `${name}.png`), fullPage: true });
}

test.describe("portfolio evidence", () => {
  test.skip(!enabled, "Run only from the manual portfolio-evidence workflow.");

  test.beforeEach(() => {
    mkdirSync(evidenceDir, { recursive: true });
  });

  test("captures the seeded coaching story", async ({ page }) => {
    expect(email).not.toBe("");
    expect(password).not.toBe("");

    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL(/\/games$/);

    await page.goto("/");
    await expect(page.getByText("CURRENT COACHING FOCUS")).toBeVisible();
    await expect(page.getByText("1568", { exact: true })).toBeVisible();
    await capture(page, "01-dashboard-desktop");

    await page.goto("/games");
    await expect(page.locator('a[href^="/games/"]').first()).toBeVisible();
    await capture(page, "02-game-library");

    const reviewHref = await page.locator('a[href^="/games/"]').first().getAttribute("href");
    expect(reviewHref).toBeTruthy();
    await page.goto(reviewHref!);
    await expect(page.locator("main")).toBeVisible();
    await capture(page, "03-game-review");

    await page.goto("/analytics");
    await expect(page.locator("main")).toBeVisible();
    await capture(page, "04-analytics-and-weakness-history");

    await page.goto("/training");
    await expect(page.locator("main")).toBeVisible();
    await capture(page, "05-training-plan");

    await page.goto("/puzzles");
    await expect(page.locator("main")).toBeVisible();
    await capture(page, "06-personal-puzzles");

    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "Admin dashboard" })).toBeVisible();
    await expect(page.getByText("Admin access is required.")).toHaveCount(0);
    await expect(page.getByText(email, { exact: true })).toBeVisible();
    await capture(page, "07-admin-operations");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await expect(page.getByText("CURRENT COACHING FOCUS")).toBeVisible();
    await capture(page, "08-dashboard-mobile");
  });
});
