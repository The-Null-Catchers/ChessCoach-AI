import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Page } from "@playwright/test";

export const evidenceEnabled = process.env.PORTFOLIO_EVIDENCE === "true";
const directory = resolve(process.cwd(), "portfolio-evidence");

export async function captureEvidence(page: Page, name: string) {
  if (!evidenceEnabled) return;
  mkdirSync(directory, { recursive: true });
  await page.screenshot({ path: resolve(directory, `${name}.png`), fullPage: true, animations: "disabled" });
}

export function recordEvidence(name: string, details: Record<string, unknown>) {
  if (!evidenceEnabled) return;
  mkdirSync(directory, { recursive: true });
  writeFileSync(resolve(directory, `${name}.json`), JSON.stringify({
    schema_version: 1,
    captured_at: new Date().toISOString(),
    tested_sha: process.env.GITHUB_SHA ?? null,
    source_sha: process.env.PORTFOLIO_SOURCE_SHA ?? null,
    run_id: process.env.GITHUB_RUN_ID ?? null,
    run_attempt: process.env.GITHUB_RUN_ATTEMPT ?? null,
    ...details,
  }, null, 2) + "\n");
}
