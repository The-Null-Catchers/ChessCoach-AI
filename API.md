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
- `GET /games`
- `POST /games/{id}/player`
- `GET /games/{id}/analysis` — move analysis, MultiPV candidates and game-review summary
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
- `GET /analytics`
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

## Operations

- `GET /admin/overview`
- `GET /admin/users`
- `POST /admin/users/{id}/suspend`
- `POST /admin/users/{id}/unsuspend`
- `GET /admin/feature-flags`
- `PUT /admin/feature-flags/{key}`

All protected endpoints require a bearer access token. Ownership checks are enforced server-side.
