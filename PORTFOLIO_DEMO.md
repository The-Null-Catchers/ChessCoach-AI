# ChessCoach AI portfolio demo

This runbook creates a deterministic, presentation-ready account without depending on Lichess, Chess.com, Stockfish, an LLM, SMTP, or push providers at demo time.

## 1. Apply migrations

From the repository root:

```bash
cd backend
alembic upgrade head
```

## 2. Seed the demo account

Choose a password locally. The seed command is intentionally guarded so it cannot run by accident.

```bash
cd backend
ALLOW_PORTFOLIO_DEMO_SEED=true \
PORTFOLIO_DEMO_EMAIL=demo@chesscoach.local \
PORTFOLIO_DEMO_PASSWORD='choose-a-local-demo-password' \
python scripts/seed_portfolio_demo.py
```

Running the command again replaces only the account matching `PORTFOLIO_DEMO_EMAIL`; it does not wipe unrelated users.

The seeded account includes:

- three analyzed games across rapid, blitz, and classical time controls
- realistic move-by-move evaluation classifications
- coaching explanations on representative critical moments
- puzzles sourced from the seeded games with spaced-repetition state
- current weaknesses plus four historical snapshots for trend charts
- opening and endgame statistics
- evidence-backed player insights
- an active weekly training plan with completed and upcoming sessions

No production credential is stored in the repository. The password exists only in the environment used to execute the seed command.

## 3. Screenshot sequence

For a concise portfolio story, capture these states in this order:

1. Dashboard — rating, recent games, current coaching focus and training status.
2. Game library — varied results, openings and time controls.
3. Game review — board, evaluation graph, critical moment and coaching explanation.
4. Analytics — weakness ranking, improvement direction, opening and endgame evidence.
5. Weakness history — show that ChessCoach tracks recurring patterns over time rather than only one-game engine scores.
6. Training — current adaptive plan and completed/upcoming sessions.
7. Puzzles — personal-game exercise with spaced repetition.
8. Admin operations — AI provider request volume, failure rate, latency and token accounting.

Use a clean desktop viewport for the primary portfolio images and one mobile screenshot to demonstrate responsive/mobile parity.

## 4. Demo narrative

A useful 60–90 second walkthrough is:

> ChessCoach AI imports a player's real games, analyzes them with Stockfish, detects recurring tactical and strategic patterns, explains the important positions at the player's level, and turns those patterns into a changing weekly training plan. The analytics page shows that the system stores historical weakness evidence, not just engine evaluations from one game. Provider telemetry and durable notification delivery demonstrate that the project is built as an operable product rather than a local chess-engine wrapper.

## Safety notes

- Keep `ALLOW_PORTFOLIO_DEMO_SEED` unset in normal environments.
- Do not use a real user's email as `PORTFOLIO_DEMO_EMAIL`; the script intentionally replaces a matching demo account.
- Do not commit the demo password to `.env`, documentation, screenshots, CI variables, or source control.
