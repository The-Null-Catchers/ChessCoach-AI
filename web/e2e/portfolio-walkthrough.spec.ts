import { expect, test, type Page } from "@playwright/test";
import { copyFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { recordEvidence } from "./evidence";

const enabled = process.env.PORTFOLIO_EVIDENCE === "true";
const evidenceDir = resolve(process.cwd(), "portfolio-evidence");

const intro = (heading: string, description: string) => `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
body{margin:0;display:grid;place-items:center;height:100vh;background:#101927;color:#f8fafc;
font:500 28px/1.45 system-ui,sans-serif}main{max-width:900px;padding:60px;text-align:center}
h1{font-size:58px;margin:0 0 22px;color:#a5b4fc}p{font-size:25px;color:#cbd5e1}
small{display:block;margin-top:30px;font-size:17px;color:#94a3b8}
</style></head><body><main><h1>${heading}</h1><p>${description}</p>
<small>ChessCoach AI · reproducible, synthetic demonstration</small></main></body></html>`;

async function chapter(page: Page, path: string, verify: () => Promise<unknown>) {
  await page.goto(path);
  await verify();
  await page.waitForTimeout(10_000);
}

test("records a versioned 60–120 second portfolio walkthrough", async ({ browser }) => {
  test.skip(!enabled, "Capture only in the isolated portfolio workflow.");
  test.setTimeout(180_000);
  const email = process.env.PORTFOLIO_DEMO_EMAIL;
  const password = process.env.PORTFOLIO_DEMO_PASSWORD;
  expect(email).toBeTruthy();
  expect(password).toBeTruthy();
  mkdirSync(evidenceDir, { recursive: true });

  // Authenticate BEFORE recording. Do not capture a password or session token
  // on screen and do not persist the browser storage state to an artifact.
  const auth = await browser.newContext();
  let state: Awaited<ReturnType<typeof auth.storageState>>;
  try {
    const login = await auth.newPage();
    await login.goto("/login");
    await login.getByLabel("Email").fill(email!);
    await login.getByLabel("Password").fill(password!);
    await login.getByRole("button", { name: "Sign in" }).click();
    await login.waitForURL(/\/games$/);
    state = await auth.storageState();
  } finally {
    await auth.close();
  }

  const context = await browser.newContext({
    storageState: state,
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: evidenceDir, size: { width: 1280, height: 720 } },
  });
  const page = await context.newPage();
  const video = page.video();
  expect(video).not.toBeNull();
  const started = Date.now();
  try {
    await page.setContent(intro("ChessCoach AI", "From game review to a personalized training plan. This walkthrough uses deterministic synthetic presentation data."));
    await page.waitForTimeout(4_000);

    await chapter(page, "/", () => expect(page.getByText("CURRENT COACHING FOCUS")).toBeVisible());
    await chapter(page, "/games", () => expect(page.locator('a[href^="/games/"]').first()).toBeVisible());
    const reviewHref = await page.locator('a[href^="/games/"]').first().getAttribute("href");
    expect(reviewHref).toMatch(/^\/games\//);
    await chapter(page, reviewHref!, () => expect(page.getByRole("heading", { name: "Learn from the critical moments" })).toBeVisible());
    await chapter(page, "/analytics", () => expect(page.getByRole("heading", { name: "Recurring weaknesses" })).toBeVisible());
    await chapter(page, "/training", () => expect(page.locator(".training-summary")).toBeVisible());
    await chapter(page, "/puzzles", () => expect(page.getByRole("heading", { name: "Find the move you missed" })).toBeVisible());

    await page.setContent(intro("Real engine evidence", "The separate real-analysis.json verifies fresh Stockfish analysis, a generated puzzle and persisted mastery. This walkthrough shows seeded presentation data."));
    // Keep the real browser capture near 85 seconds, with a 60–120 second
    // duration gate in CI. Fail rather than claim an unverified length.
    await page.waitForTimeout(Math.max(5_000, 85_000 - (Date.now() - started)));
  } finally {
    await context.close();
  }

  const raw = await video!.path();
  copyFileSync(raw, resolve(evidenceDir, "portfolio-walkthrough.webm"));
  recordEvidence("walkthrough", {
    kind: "real Playwright browser recording with introductory/outro cards",
    data_origin: "deterministic synthetic portfolio seed; NOT a fresh engine run",
    real_engine_analysis: false,
    browser_version: browser.version(),
    chapters: ["dashboard", "games", "game review", "analytics", "training", "puzzles"],
    file: "portfolio-walkthrough.webm",
    duration_seconds: "verified by ffprobe in the CI workflow",
    credentials_recorded: false,
    note: "A separate real-analysis.json manifest documents the real Stockfish scenario.",
  });
});
