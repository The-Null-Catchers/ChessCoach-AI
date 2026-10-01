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


test("runs the critical coaching loop from PGN import through puzzle mastery", async ({ page }) => {
  test.setTimeout(120_000);

  const email = `coach-e2e-${Date.now()}@example.com`;
  await page.goto("/login");
  await page.getByRole("button", { name: "Need an account? Register" }).click();
  await page.getByLabel("Display name").fill("E2E Player");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("e2e-secure-password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/games$/);

  await page.goto("/import");
  await page.getByLabel("Your chess username or PGN player name").fill("E2E Player");
  await page.getByLabel("Analysis strength").selectOption("normal");
  await page.locator('textarea[name="pgn"]').fill(`[Event "Critical Coaching E2E"]
[Site "CI"]
[Date "2026.10.01"]
[Round "1"]
[White "E2E Player"]
[Black "Opponent"]
[Result "0-1"]
[TimeControl "300+0"]

1. f3 e5 2. g4 Qh4# 0-1`);
  await page.getByRole("button", { name: "Analyze PGN" }).click();

  await expect(page.getByText("Queued for analysis")).toBeVisible();
  await expect(page.getByText(/Analysis: complete · 100%/)).toBeVisible({ timeout: 90_000 });

  const gameLink = page.getByRole("link", { name: "Open game" }).first();
  const href = await gameLink.getAttribute("href");
  expect(href).toMatch(/^\/games\//);
  const gameId = href!.split("/").pop()!;

  await gameLink.click();
  await expect(page.getByText("Analysis complete")).toBeVisible();
  const blunderMove = page.getByRole("button", { name: /3\. g4/ });
  await expect(blunderMove).toBeVisible();
  await blunderMove.click();
  await expect(page.locator(".coach-note")).toBeVisible();

  const token = await page.evaluate(() => window.localStorage.getItem("chesscoach_access_token"));
  expect(token).toBeTruthy();
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
  const headers = { Authorization: `Bearer ${token}` };

  const analysisResponse = await page.request.get(`${apiBase}/games/${gameId}/analysis`, { headers });
  expect(analysisResponse.ok()).toBeTruthy();
  const analysis = await analysisResponse.json() as {
    moves: Array<{
      fen_before: string;
      analysis: null | { best_move: string | null; classification: string };
    }>;
  };

  const puzzlesResponse = await page.request.get(`${apiBase}/puzzles?limit=20`, { headers });
  expect(puzzlesResponse.ok()).toBeTruthy();
  const puzzles = await puzzlesResponse.json() as Array<{
    id: string;
    fen: string;
    source_game_id: string | null;
  }>;
  const puzzle = puzzles.find((item) => item.source_game_id === gameId);
  expect(puzzle).toBeTruthy();

  const sourceMove = analysis.moves.find((item) => item.fen_before === puzzle!.fen);
  expect(sourceMove?.analysis?.best_move).toBeTruthy();
  const bestMove = sourceMove!.analysis!.best_move!;
  const from = bestMove.slice(0, 2);
  const to = bestMove.slice(2, 4);

  await page.goto("/puzzles");
  await expect(page.getByRole("heading", { name: "Find the move you missed" })).toBeVisible();
  await page.getByRole("button", { name: from }).click();
  await page.getByRole("button", { name: to }).click();
  await expect(page.getByText("Correct. How difficult was this recall?")).toBeVisible();
  await page.getByRole("button", { name: "Good" }).click();

  const trainingResponse = await page.request.get(`${apiBase}/training`, { headers });
  expect(trainingResponse.ok()).toBeTruthy();
  const training = await trainingResponse.json() as {
    reviewed_puzzles: number;
    puzzle_mastery: number;
  };
  expect(training.reviewed_puzzles).toBeGreaterThanOrEqual(1);
  expect(training.puzzle_mastery).toBeGreaterThan(0);
});
