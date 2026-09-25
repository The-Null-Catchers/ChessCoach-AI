import { expect, test } from "@playwright/test";

test("registers, opens the game library, and reaches admin operations", async ({ page }) => {
  await page.goto("/login");

  await page.getByRole("button", { name: "Need an account? Register" }).click();
  await page.getByLabel("Display name").fill("E2E Admin");
  await page.getByLabel("Email").fill("admin-e2e@example.com");
  await page.getByLabel("Password").fill("e2e-secure-password");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/games$/);
  await expect(page.getByRole("heading", { name: "Game library" })).toBeVisible();
  await expect(page.getByText("No games imported yet.")).toBeVisible();

  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Admin dashboard" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Runtime product controls" })).toBeVisible();
  await expect(page.getByText("weekly reports")).toBeVisible();

  const weeklyFlag = page.locator(".flag-row").filter({ hasText: "weekly reports" });
  await weeklyFlag.getByRole("button", { name: "Enabled" }).click();
  await expect(weeklyFlag.getByRole("button", { name: "Disabled" })).toBeVisible();

  await page.reload();
  await expect(page.locator(".flag-row").filter({ hasText: "weekly reports" }).getByRole("button", { name: "Disabled" })).toBeVisible();
});
