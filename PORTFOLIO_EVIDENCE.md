# Portfolio evidence automation

ChessCoach AI includes a GitHub Actions workflow named **Portfolio Evidence** that creates a clean showcase environment and captures two explicitly separate stories: deterministic presentation data and a fresh PGN processed by real Stockfish.

## What the workflow does

1. Starts isolated PostgreSQL and Redis services on the GitHub-hosted runner.
2. Applies Alembic migrations.
3. Generates a random, masked password for an ephemeral demo account.
4. Runs the guarded `seed_portfolio_demo.py` script.
5. Grants admin access only after a second explicit guard verifies the account contains `portfolio_demo` games.
6. Starts the FastAPI and Next.js applications locally on the runner.
7. Starts Stockfish-backed Celery analysis and records the installed engine's UCI identity.
8. Runs the dedicated presentation spec and the existing critical-coaching-loop browser test, including fresh PGN import, real worker completion, positive analysis depths, engine review, a personal puzzle and persisted mastery.
9. Uploads screenshots, success-path browser videos, JSON evidence manifests and the Playwright report as a 30-day workflow artifact.

The seeded presentation story does not run Stockfish. The separate real-analysis story does run local Stockfish and Celery. Neither story contacts Lichess, Chess.com, a hosted LLM, external SMTP, push providers or the production deployment. Coaching explanations use the deterministic template provider, not a hosted AI model.

## Captured evidence

The artifact contains:

- `01-dashboard-desktop.png`
- `02-game-library.png`
- `03-game-review.png`
- `04-analytics-and-weakness-history.png`
- `05-training-plan.png`
- `06-personal-puzzles.png`
- `07-admin-operations.png`
- `08-dashboard-mobile.png`
- `09-real-stockfish-review.png`
- `10-real-game-puzzle.png`
- `11-real-puzzle-solved.png`
- `12-real-training-after-review.png`
- `seeded-story.json` — marks synthetic historical progress explicitly.
- `real-analysis.json` — records engine identity, PGN SHA-256, analysis depths/profiles, import-to-completion wall time, source-puzzle linkage and persisted mastery after successful assertions.

Both manifests record the tested checkout SHA, source/head SHA, run ID and attempt. On a pull request, GitHub's tested checkout can be a synthetic merge commit; do not label it as the source SHA or an already-published release.

Browser recordings are under the `test-results` subdirectories of the artifact. They are raw workflow recordings, not a finished promotional video. Screenshots 01–08 are presentation fixtures; 09–12 come from the newly imported game. The four-ply synthetic game is deliberately small and is not a representative performance benchmark. Its wall time includes queue and browser polling overhead.

These images cover the core portfolio story: persisted coaching data, analyzed games, rich review, historical weakness evidence, adaptive training, personal puzzles, operational tooling, and responsive UI.

## Running it

From GitHub, open **Actions → Portfolio Evidence → Run workflow** on the commit or branch you want to document.

It also runs on pull requests to `main` and pushes to `main` that change the evidence workflow, browser tests/config, or portfolio Markdown files. Unrelated changes do not trigger this extra capture job. Use manual dispatch when capturing another application change for release evidence.

## Preserving a release bundle

1. Verify the workflow passed at the intended commit; inspect both JSON manifests.
2. Inspect the screenshots and videos for readable content and accidental credential exposure. Never publish traces, service logs, API tokens or environment files.
3. Download the artifact before its 30-day expiry and retain the approved media/manifests with that release's evidence. An expiring Actions artifact URL is not a permanent portfolio link.
4. Link the retained bundle, source SHA and passing run from the release notes/case study. Publish a benchmark only after a separate representative workload measurement.

Missing screenshots or failed assertions fail capture rather than creating a successful evidence claim. Failure artifacts may be partial; only a successful run with both manifests counts as the complete bundle.

## Admin safety

The normal demo seed deliberately creates a non-admin account. Admin promotion is separated into `backend/scripts/enable_portfolio_demo_admin.py` and requires:

```bash
ALLOW_PORTFOLIO_DEMO_ADMIN=true
PORTFOLIO_DEMO_EMAIL=<seeded-demo-email>
```

The script refuses to promote an arbitrary account: it verifies that the target user exists and owns at least one game whose source is `portfolio_demo`.

Do not run the admin-promotion helper against a real user account or production database. The automated workflow runs it only inside an ephemeral CI database.
