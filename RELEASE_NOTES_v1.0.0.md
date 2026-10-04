# ChessCoach AI v1.0.0

ChessCoach AI v1.0.0 is the first portfolio-ready release of the intelligent chess training platform.

## What makes this release different

ChessCoach AI is not a Stockfish wrapper. It turns real player games into a coaching loop:

1. import games from PGN, Lichess, or Chess.com;
2. analyze critical positions with Stockfish and cached MultiPV lines;
3. classify tactical, strategic, opening, endgame, and time-management mistakes;
4. explain important positions at the player's level using a provider-neutral AI layer with deterministic fallback;
5. aggregate recurring weaknesses and track how they change over time;
6. generate personal puzzles and spaced-repetition reviews from the player's own games;
7. build an adaptive weekly training plan from persisted evidence.

## Highlights

- Production-oriented FastAPI/PostgreSQL/Redis/Celery architecture.
- Persistent Stockfish worker engines with quick/normal/deep analysis profiles.
- Rich web game review with evaluation graph, critical moments, MultiPV, and coaching explanations.
- Flutter mobile client with legal-move board interaction, offline caches, queued puzzle attempts, and persistent auth.
- Lichess and Chess.com account imports with bounded fetches, duplicate handling, and SSRF-hardened provider URL validation.
- Historical weakness snapshots and improving/stable/worsening trend comparisons.
- Opening repertoire and endgame technique trainers.
- Durable push-notification outbox with bounded retries and provider-neutral webhook delivery.
- AI provider usage telemetry for requests, failures, fallback behavior, latency, request IDs, and token counts.
- Admin operations for account controls, feature flags, audit logging, and operational metrics.
- Weekly reports, in-app notifications, and scheduled email delivery.

## Security and reliability

- Argon2 password hashing.
- JWT access tokens plus persisted refresh-session rotation and replay detection.
- Hashed one-time verification/reset tokens.
- Redis-backed rate limiting and per-user abuse controls.
- Dependency, vulnerability, secret, and misconfiguration scanning in CI.
- Chess.com provider import trust-boundary hardening against SSRF and redirect pivots.
- Dependency-aware readiness checks, structured logs, and request IDs.

## Validation evidence

The release candidate passed the repository's backend, web, Flutter, Docker, security, Playwright browser E2E, and mobile smoke gates before release preparation.

The portfolio demo is deterministic and does not require external chess providers, an LLM, SMTP, or push delivery at presentation time. See `PORTFOLIO_DEMO.md` for the guarded seed command and screenshot sequence.

## Release checklist

- [x] API version set to `1.0.0`
- [x] mobile package version set to `1.0.0+12`
- [x] changelog added
- [x] deterministic demo seed documented
- [x] portfolio screenshot/runbook documented
- [ ] merge this release-prep PR after CI/E2E pass
- [ ] create GitHub tag `v1.0.0`
- [ ] create GitHub Release using these notes
- [ ] attach final screenshots/demo video if desired
