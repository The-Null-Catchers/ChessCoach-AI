import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { captureEvidence, evidenceEnabled, recordEvidence } from "./evidence";

test("shows structured sign-in validation errors without crashing", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("invalid@chesscoach.local");
  await page.getByLabel("Password").fill("e2e-secure-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator(".form-error")).toHaveText("Check your email address and password, then try again.");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByLabel("Email").fill("missing-e2e-user@example.com");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.locator(".form-error")).toHaveText("Invalid credentials");
});

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
  const pgn = `[Event "Critical Coaching E2E"]
[Site "CI"]
[Date "2026.10.01"]
[Round "1"]
[White "E2E Player"]
[Black "Opponent"]
[Result "0-1"]
[TimeControl "300+0"]

1. f3 e5 2. g4 Qh4# 0-1`;
  await page.locator('textarea[name="pgn"]').fill(pgn);
  const analysisStarted = Date.now();
  await page.getByRole("button", { name: "Analyze PGN" }).click();

  await expect(page.getByText("Queued for analysis")).toBeVisible();
  await expect(page.getByText(/Analysis: complete · 100%/)).toBeVisible({ timeout: 90_000 });
  const importToCompletionMs = Date.now() - analysisStarted;

  const gameLink = page.getByRole("link", { name: "Open game" }).first();
  const href = await gameLink.getAttribute("href");
  expect(href).toMatch(/^\/games\//);
  const gameId = href!.split("/").pop()!;

  await gameLink.click();
  await expect(page.getByText("Analysis complete")).toBeVisible();
  const blunderMove = page.locator(".move-list .move-chip").filter({ hasText: "3. g4" });
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
      analysis: null | {
        best_move: string | null;
        classification: string;
        depth: number;
        profile: string;
        cpl: number | null;
        mate_after: number | null;
        checkmate: boolean;
      };
    }>;
  };
  expect(analysis.moves).toHaveLength(4);
  for (const move of analysis.moves) {
    expect(move.analysis).not.toBeNull();
    expect(move.analysis!.depth).toBeGreaterThan(0);
    expect(move.analysis!.profile).toBe("normal");
  }
  expect(analysis.moves[2].analysis).toMatchObject({ classification: "blunder", cpl: null, mate_after: -1 });
  expect(analysis.moves[3].analysis).toMatchObject({ cpl: null, mate_after: 0, checkmate: true });
  await expect(page.getByRole("button", { name: "Biggest mistake · g4" })).toBeVisible();
  const graph = page.getByRole("img", { name: "Engine evaluation graph" });
  await expect(graph.locator("circle")).toHaveCount(4);
  await expect(graph.locator("title").last()).toHaveText("Ply 4: Checkmate");
  await expect(page.locator(".move-heading strong")).toHaveText("M-1");

  const analyticsResponse = await page.request.get(`${apiBase}/analytics`, { headers });
  expect(analyticsResponse.ok()).toBeTruthy();
  const analytics = await analyticsResponse.json();
  const measuredLoss = analysis.moves[0].analysis!.cpl!;
  const expectedAccuracy = Number((100 * Math.exp(-(measuredLoss + 350) / 700)).toFixed(2));
  expect(analytics.overview.average_centipawn_loss).toBe(measuredLoss);
  expect(analytics.overview.accuracy).toBe(expectedAccuracy);
  expect(analytics.overview.phase_accuracy.opening).toBe(expectedAccuracy);
  expect(analytics.openings[0].average_accuracy).toBe(expectedAccuracy);
  await captureEvidence(page, "09-real-stockfish-review");

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
  await captureEvidence(page, "10-real-game-puzzle");
  await page.getByRole("button", { name: from }).click();
  await page.getByRole("button", { name: to }).click();
  await expect(page.getByText("Correct. How difficult was this recall?")).toBeVisible();
  await captureEvidence(page, "11-real-puzzle-solved");
  await page.getByRole("button", { name: "Good" }).click();
  await expect(page.getByText("Correct. How difficult was this recall?")).not.toBeVisible();

  const trainingResponse = await page.request.get(`${apiBase}/training`, { headers });
  expect(trainingResponse.ok()).toBeTruthy();
  const training = await trainingResponse.json() as {
    reviewed_puzzles: number;
    puzzle_mastery: number;
  };
  expect(training.reviewed_puzzles).toBeGreaterThanOrEqual(1);
  expect(training.puzzle_mastery).toBeGreaterThan(0);

  await page.goto("/training");
  await expect(page.locator(".training-summary")).toBeVisible();
  await captureEvidence(page, "12-real-training-after-review");
  if (evidenceEnabled) {
    expect(process.env.PORTFOLIO_ENGINE_NAME).toMatch(/Stockfish/i);
  }
  recordEvidence("real-analysis", {
    scenario: "PGN import -> Stockfish worker -> game review -> personal puzzle -> persisted mastery",
    data_origin: "fresh synthetic four-ply PGN, analyzed by the real engine; not demo seed",
    engine_name: process.env.PORTFOLIO_ENGINE_NAME ?? null,
    ai_provider: "template",
    pgn_sha256: createHash("sha256").update(pgn).digest("hex"),
    import_to_completion_ms: importToCompletionMs,
    analysis: analysis.moves.map((move) => move.analysis),
    puzzle_source_matches_import: puzzle!.source_game_id === gameId,
    reviewed_puzzles: training.reviewed_puzzles,
    puzzle_mastery: training.puzzle_mastery,
  });
});
