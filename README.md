# ChessCoach AI

A production-oriented intelligent chess training platform that learns from a player's real games. Stockfish supplies objective analysis; higher-level classifiers and AI coaching turn critical moments into personalized training.

## What is implemented in Phase 1

- FastAPI service with Argon2 password hashing and JWT auth
- PostgreSQL domain model for users, games, moves, analyses, mistakes, weaknesses and puzzles
- multi-game PGN parsing and per-user duplicate detection
- FEN/PGN persistence and normalized position hashing foundation
- asynchronous Stockfish analysis through Celery + Redis
- context-aware move classification (not a raw fixed-CPL wrapper)
- analysis-job progress endpoint
- Next.js responsive coaching dashboard foundation
- Flutter/Riverpod mobile foundation with original chess-product visual language
- Docker Compose for PostgreSQL, Redis, API, worker and web
- GitHub Actions for backend, web, Flutter APK artifact and Docker validation
- unit tests for PGN parsing and move classification

## Architecture

`web/` Next.js UI → `backend/` FastAPI → PostgreSQL

Long-running analysis is dispatched to Celery through Redis. The analysis worker owns Stockfish execution, keeping HTTP requests non-blocking. AI explanations, weakness recomputation, puzzle generation and aggregation are designed as additional worker stages, not API-thread work.

## Run locally

```bash
docker compose up --build
```

API: `http://localhost:8000`  
OpenAPI: `http://localhost:8000/docs`  
Web: `http://localhost:3000`

## First E2E target

Register → import PGN → queue analysis → poll job → inspect analyzed moves → generate puzzle from a critical mistake → record attempt → update weakness/training state.

## Engineering direction

The next phases should add refresh-token session persistence/rotation, semantic mistake detectors, cached engine analysis, AI-provider abstraction, WebSocket/SSE progress, real game-review board, personalized spaced repetition, analytics aggregations, opening/endgame profiling and the complete automated E2E flow.
