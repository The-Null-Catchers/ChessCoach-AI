# Changelog

All notable changes to ChessCoach AI are documented here.

## [1.0.0] - 2026-10-04

### Product
- End-to-end coaching loop from real-game import through Stockfish analysis, semantic mistake detection, AI explanation, weakness tracking, personalized puzzles, spaced repetition, and adaptive weekly training.
- Lichess and Chess.com account imports with duplicate detection, bounded fetches, account linking, and hardened provider trust boundaries.
- Rich game review with evaluation graph, critical moments, MultiPV candidate lines, move classifications, and level-aware coaching explanations.
- Historical weakness snapshots with improving, stable, and worsening trend analysis across tactical, strategic, opening, endgame, and time-management themes.
- Opening repertoire trainer, curated endgame technique trainer, personal-game puzzle generation, and adaptive training plans.

### Clients
- Next.js web dashboard covering authentication, game import/library/review, analytics, puzzles, training, admin operations, and responsive layouts.
- Flutter/Riverpod mobile application with persistent sessions, dark mode, legal-move chessboard interaction, offline caches, queued puzzle attempts, and API parity for the core training flow.

### Platform and operations
- FastAPI, PostgreSQL, Redis, Celery, Alembic, Docker Compose, and persistent Stockfish worker processes.
- Provider-neutral push notification subscriptions, transactional delivery outbox, bounded retries, and webhook delivery for FCM/APNs gateways.
- AI provider usage telemetry including latency, request outcome, token counts, request IDs, failure/fallback tracking, and admin aggregation.
- Request IDs, structured logs, readiness checks, audit logs, feature flags, account suspension, session revocation, and per-user abuse controls.
- Weekly progress reports with in-app notification state and scheduled email delivery.

### Security
- Argon2 password hashing, access/refresh token rotation with replay detection, hashed one-time auth-action tokens, abuse rate limiting, and audit logging.
- Hardened Chess.com import URL validation and redirect handling to prevent SSRF through provider metadata.
- CI dependency audits plus vulnerability, secret, and misconfiguration scanning.

### Quality and release evidence
- Backend, web, Flutter, and Docker CI gates.
- Automated Playwright browser E2E against the real API and analysis worker.
- Deterministic hosted-runner Android smoke coverage plus real Android-emulator integration coverage where supported.
- Guarded deterministic portfolio demo seed with analyzed games, coaching explanations, puzzles, weakness history, insights, and training data.
- Portfolio demo and screenshot runbook in `PORTFOLIO_DEMO.md`.
