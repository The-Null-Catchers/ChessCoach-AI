# Portfolio evidence automation

ChessCoach AI includes a manual GitHub Actions workflow named **Portfolio Evidence** that creates a clean, deterministic showcase environment and captures repeatable screenshots as a workflow artifact.

## What the workflow does

1. Starts isolated PostgreSQL and Redis services on the GitHub-hosted runner.
2. Applies Alembic migrations.
3. Generates a random, masked password for an ephemeral demo account.
4. Runs the guarded `seed_portfolio_demo.py` script.
5. Grants admin access only after a second explicit guard verifies the account contains `portfolio_demo` games.
6. Starts the FastAPI and Next.js applications locally on the runner.
7. Runs a dedicated Playwright evidence spec.
8. Uploads the screenshots and Playwright report as a 30-day workflow artifact.

The workflow does not contact Lichess, Chess.com, Stockfish, an LLM, SMTP, push providers, or the production deployment.

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

These images cover the core portfolio story: persisted coaching data, analyzed games, rich review, historical weakness evidence, adaptive training, personal puzzles, operational tooling, and responsive UI.

## Running it

From GitHub, open **Actions → Portfolio Evidence → Run workflow** on the commit or branch you want to document.

The workflow is `workflow_dispatch` only. Normal pushes and pull requests do not create portfolio evidence artifacts automatically.

## Admin safety

The normal demo seed deliberately creates a non-admin account. Admin promotion is separated into `backend/scripts/enable_portfolio_demo_admin.py` and requires:

```bash
ALLOW_PORTFOLIO_DEMO_ADMIN=true
PORTFOLIO_DEMO_EMAIL=<seeded-demo-email>
```

The script refuses to promote an arbitrary account: it verifies that the target user exists and owns at least one game whose source is `portfolio_demo`.

Do not run the admin-promotion helper against a real user account or production database. The automated workflow runs it only inside an ephemeral CI database.
