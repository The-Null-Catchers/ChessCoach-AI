# Architecture

## Service boundaries

- **API service:** authentication, authorization, imports, queries, training interactions and lightweight health endpoints.
- **Analysis worker:** Stockfish execution, deterministic chess calculations and cache population.
- **Coaching pipeline:** schema-validated AI explanations generated only for useful engine-backed moments.
- **Aggregation pipeline:** weakness confidence, trends, opening/endgame statistics, insights and training-plan inputs.
- **Web:** responsive Next.js coaching experience.
- **Mobile:** Flutter/Riverpod client with offline read caches and queued puzzle-attempt synchronization.
- **PostgreSQL:** durable domain and analytics state.
- **Redis:** Celery broker/backend and realtime/background coordination.

## Analysis invariants

1. Stockfish is authoritative for objective evaluation.
2. LLM output cannot overwrite engine scores, best moves or mate results.
3. Expensive work never runs synchronously in a normal HTTP request.
4. Identical normalized positions converge on shared cached engine results.
5. Long-term weakness statements require sample-size-aware confidence.
6. Coaching analytics only use moves that belong to the authenticated player.
7. Read endpoints do not silently trigger expensive recomputation.

## Processing flow

1. A client imports one or more PGNs.
2. The API validates/parses input, performs duplicate detection and persists games/moves.
3. Analysis jobs are queued through Redis.
4. Workers analyze positions with Stockfish and reuse cached normalized positions.
5. Deterministic semantic detectors attach tactical, positional or time-management themes.
6. Weakness/opening/endgame aggregations are recomputed from persisted player-owned evidence.
7. Selected critical moments may receive a structured AI explanation.
8. User-game puzzles and spaced-repetition state feed the training plan.
9. Clients receive progress over SSE and fetch completed review/analytics data.

## Reliability and observability

- analysis jobs store status, progress and error state
- retries are designed to be idempotent
- `/health` is a cheap liveness endpoint
- `/health/ready` checks PostgreSQL, Redis and the configured Stockfish executable
- each HTTP response receives an `X-Request-ID`
- HTTP logs are structured and record request ID, method, path, status and duration without logging query strings
