# ChessCoach AI

ChessCoach AI is a production-oriented intelligent chess training platform that learns from a player's real games. Stockfish supplies objective chess analysis; deterministic classifiers, statistics, spaced repetition and an AI coaching layer turn critical moments into personalized training.

## Current implementation

The repository now includes the core end-to-end coaching loop rather than a UI-only prototype:

- FastAPI + PostgreSQL backend with Argon2 password hashing and JWT access tokens
- persisted refresh-token families with rotation, replay detection, logout and logout-all
- one-time email verification and password-reset flows with hashed expiring tokens
- Redis-backed abuse rate limiting for sensitive authentication endpoints
- multi-game PGN parsing, duplicate detection, player-side identification and clock extraction
- asynchronous Stockfish analysis through Celery + Redis
- normalized position hashing and cached engine analysis
- context-aware move classification with mate-aware handling
- semantic mistake detection, normalized mistake taxonomy and player-only weakness aggregation
- deterministic tactical motif detection for hanging pieces, forks and absolute pins
- time-management themes when clock data is available
- structured AI coaching with provider abstraction and deterministic fallback
- SSE analysis progress
- user-game puzzle generation and spaced repetition (Again / Hard / Good / Easy)
- adaptive weekly training plans and session tracking
- analytics for phase accuracy, openings, endgames, weaknesses and evidence-based insights
- normalized opening repertoire move trees with PGN variation import and spaced-repetition training
- curated endgame technique trainer with legal-move validation, mastery tracking and spaced repetition
- Next.js dashboard, auth, import, game library, game review, puzzles, training and analytics
- Flutter/Riverpod app with real API auth, offline caches, queued offline puzzle attempts and dark mode
- interactive Flutter chessboard with legal moves, tap/drag movement, promotion, board flip and review navigation
- Docker Compose for PostgreSQL, Redis, API, worker and web
- CI for backend, web, Flutter tests/builds and Docker validation
- CI security gates for Python/Node dependencies plus repository vulnerability, secret and misconfiguration scanning
- manual production Android workflow that builds a signed AAB from protected GitHub Environment secrets and emits a SHA-256 checksum
- dependency-aware readiness checks plus request IDs and structured HTTP request logs
- admin operations API with account suspension, session revocation, audit logging and per-user abuse limits for expensive operations
- idempotent weekly progress reports with in-app notifications, read state and scheduled email delivery

## Architecture

`web/` Next.js and `mobile/` Flutter are clients of the FastAPI service in `backend/`.

Long-running chess work never runs inside normal HTTP request handling. Celery workers consume jobs through Redis and own Stockfish execution. The API persists analysis state in PostgreSQL and exposes live progress through SSE.

Stockfish is the objective source of truth. Semantic detectors and the LLM coaching layer may explain or classify engine-backed positions, but they cannot replace engine scores, best moves or mate results.

## Run locally

```bash
docker compose up --build
```

API: `http://localhost:8000`  
OpenAPI: `http://localhost:8000/docs`  
Liveness: `http://localhost:8000/health`  
Readiness: `http://localhost:8000/health/ready`  
Web: `http://localhost:3000`

## Main user flow

Register → import PGN → analysis worker processes the game → inspect critical moments and coaching explanations → receive a puzzle generated from the user's own game → solve and grade it → spaced repetition and weakness statistics update → training plan adapts.

## Engineering principles

1. Stockfish is authoritative for objective evaluation.
2. The LLM is an explanatory coach, not the chess oracle.
3. Expensive work is asynchronous and idempotent.
4. Cached normalized positions avoid repeated engine work.
5. Long-term weakness claims are sample-size and confidence aware.
6. Analytics are generated from persisted player data, not hardcoded demo claims.
7. Mobile offline writes are queued and synchronized safely when connectivity returns.

## Near-term roadmap

- admin/operations dashboard and feature flags
- full automated browser/mobile E2E workflow
