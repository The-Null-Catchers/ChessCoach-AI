# API

Current API prefix: `/api/v1`.

FastAPI publishes generated OpenAPI at `/openapi.json` and interactive documentation at `/docs`.

## Authentication

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/logout-all`
- `POST /auth/verify-email/request`
- `POST /auth/verify-email/confirm`
- `POST /auth/password-reset/request`
- `POST /auth/password-reset/confirm`

## Games and analysis

- `POST /games/import` — PGN text/file import; accepts `analysis_strength=quick|normal|deep`
- `POST /games/import/account` — import up to 50 recent public games from `lichess` or `chesscom`, persist the connected account, deduplicate, and queue analysis
- `GET /games`
- `POST /games/{id}/player`
- `GET /games/{id}/analysis` — move analysis, MultiPV candidates and game-review summary
  - `mate_before` and `mate_after` are nullable integers from the mover's perspective. Positive favors the mover, negative favors the opponent, and zero after the move means the mover delivered checkmate. `checkmate` also identifies a terminal checkmate in older analyses without an explicit mate value. The graph uses White's perspective for vertical placement.
  - `cpl` and average centipawn loss use measured centipawn loss only. Estimated accuracy retains the existing exponential calculation. A mate blunder contributes a scoring weight of 350, a mate mistake 150, and other mate decisions zero. These weights are inputs to accuracy only. Moves without a recorded centipawn loss or mate decision are omitted. A group with no scoreable samples reports null accuracy.
  - Game and overview accuracy use the stored moves immediately. Opening and endgame summaries are persisted and recalculate when a game is analyzed. To refresh an existing account without running Stockfish, run `python -m scripts.refresh_player_analytics USER_ID` from `backend/` against the upgraded database while analysis for that account is idle.
- `GET /games/{id}/mistakes`
- `GET /analysis-jobs/{id}`
- `GET /analysis-jobs/{id}/events` — Server-Sent Events progress

## Coaching and puzzles

- `GET /profile/weaknesses`
- `GET /puzzles`
- `GET /puzzles/queue`
- `POST /puzzles/{id}/attempt`
- `POST /puzzles/{id}/grade`

## Training and analytics

- `GET /training`
- `POST /training/{session_id}/complete`
- `GET /analytics` — current performance, weaknesses and one-step weakness trend direction
- `GET /analytics/weakness-history` — historical weakness snapshots with long-term score delta and improving/stable/worsening direction; optional `category` and `limit` (1–52)
- `GET /openings`
- `GET /endgames`
- `GET /insights`

## Opening repertoires

- `POST /repertoires`
- `GET /repertoires`
- `GET /repertoires/{id}`
- `POST /repertoires/{id}/import-pgn`
- `GET /repertoires/{id}/training`
- `POST /repertoires/{id}/lines/{line_id}/attempt`

## Endgame trainer

- `GET /endgames/trainer/overview`
- `GET /endgames/trainer/queue`
- `POST /endgames/trainer/{exercise_id}/attempt`

## Reports and notifications

- `GET /reports/weekly`
- `POST /reports/weekly/current`
- `GET /notifications`
- `POST /notifications/{id}/read`
- `POST /notifications/read-all`
- `GET /notifications/push/subscriptions` — list the authenticated user's registered devices without exposing push tokens
- `POST /notifications/push/subscriptions` — register or reactivate an Android, iOS or web push token
- `DELETE /notifications/push/subscriptions/{subscription_id}` — deactivate a device subscription

Push delivery uses a transactional outbox (`push_deliveries`) so notification creation and delivery intent are committed together. Delivery is asynchronous through Celery, retry-bounded, idempotent per notification/device pair, and disabled by default. Production can set `PUSH_PROVIDER=webhook` to forward normalized payloads to an FCM/APNs gateway without coupling the product domain to a specific vendor.

## Operations

- `GET /admin/overview`
- `GET /admin/users`
- `POST /admin/users/{id}/suspend`
- `POST /admin/users/{id}/unsuspend`
- `GET /admin/feature-flags`
- `PUT /admin/feature-flags/{key}`

All protected endpoints require a bearer access token. Ownership checks are enforced server-side.
