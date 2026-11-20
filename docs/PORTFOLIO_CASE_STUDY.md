# ChessCoach AI | Portfolio case study

## Problem and outcome

A chess player can receive an engine score for a game yet still struggle to turn it into useful practice. ChessCoach AI connects PGN import, asynchronous Stockfish analysis, a readable critical-moment review, a personal puzzle from the game, and persistent training progress. The goal is a complete coaching loop, not merely a chessboard or a model-generated explanation.

**Demonstration:** [Portfolio runbook](../PORTFOLIO_DEMO.md) · [Evidence guide](../PORTFOLIO_EVIDENCE.md) · [CI](https://github.com/The-Null-Catchers/ChessCoach-AI/actions/workflows/ci.yml) · [E2E](https://github.com/The-Null-Catchers/ChessCoach-AI/actions/workflows/e2e.yml).

## Architecture and two decisions

**1. Keep objective analysis separate from generated language.** Stockfish and the persisted analysis records own evaluations, candidate lines, mate scores, and tactical outcomes. A deterministic classifier interprets positions, while the coaching provider explains results. The template fallback can continue to explain an already-analyzed game if a hosted model is unavailable; it does not replace the engine. Alternative considered: ask a language model to evaluate chess positions directly. Rejected because explanations cannot reliably substitute for reproducible engine scores.

**2. Move expensive analysis to durable workers.** FastAPI accepts PGN imports and records analysis jobs; Celery workers run Stockfish through Redis, with PostgreSQL persisting games, results, puzzle lineage and training history. The browser follows progress instead of holding a long-running analysis inside a request. Alternative considered: analyze synchronously in the HTTP handler. Rejected because engine work can outlast request timeouts and tie up API capacity.

## Tested user journey

1. A synthetic player signs in, imports the four-ply `1. f3 e5 2. g4 Qh4#` PGN, and receives a queued analysis job.
2. A real Stockfish worker completes the job. The review exposes the critical mistake, mate score and candidate line.
3. A puzzle sourced from that game is solved and graded. Training progress is retrieved again after reopening the page.
4. Reanalysis of the same game completes and preserves the expected forced-mate classification.

This is checked by `web/e2e/auth-admin.spec.ts`. The separate presentation account contains **seeded, synthetic history** and is not evidence of live engine computation. The capture workflow generates `real-analysis.json` and `seeded-story.json` to keep these stories distinct.

## Failure handling and boundaries

The app tests malformed sign-in input and absent accounts without crashing. Engine work has explicit queued/complete states and reanalysis checks; the E2E flow verifies persisted results after page navigation. Provider-generated coaching is not used as the source of truth for engine results. The short four-ply PGN is a functional fixture, **not** a representative latency benchmark.

The automated portfolio run uses isolated PostgreSQL/Redis, Stockfish, a template coaching provider and ephemeral credentials. It does not verify Lichess/Chess.com availability, hosted LLM quality, push/SMTP integrations, production uptime or physical mobile-device performance.

## Presentation bundle

The workflow produces 12 screenshots (eight seeded UI views and four fresh-engine views), JSON evidence manifests, Playwright browser recordings and `portfolio-walkthrough.webm`. The walkthrough is a **real browser recording of seeded UI**, with chapter holds and visible disclosure. The workflow rejects a finished recording outside 60–120 seconds. It is not a narration or a recording of the separate real-engine scenario.

The artifact has limited GitHub retention. Before sharing publicly, review images and video for accidental secrets, preserve an approved copy in durable storage, and link it with the exact tested SHA and CI run. Do not claim a published release or final video until those checks pass.

## Reproduce and review

From a clean checkout, follow [the Docker quick start](../README.md), then use [the guarded seed procedure](../PORTFOLIO_DEMO.md). To reproduce the automated run, execute the Portfolio Evidence workflow on a known commit and inspect `walkthrough.json`, `real-analysis.json`, `seeded-story.json`, and the Playwright report. The workflow's own logs and artifact are the acceptance record. For public redistribution, the repository still needs an explicit licensing and contributor-attribution decision.
