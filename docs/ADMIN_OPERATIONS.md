# Admin operations

ChessCoach AI includes a small, auditable operations surface for account safety and abuse response.

## Bootstrap an administrator

Set `ADMIN_EMAILS` to a comma-separated allowlist before the administrator registers or signs in:

```env
ADMIN_EMAILS=ops@example.com,security@example.com
```

A matching account receives `is_admin=true`. This grant is recorded in the audit log when it occurs during sign-in.

## Operations endpoints

All endpoints require an authenticated account with `is_admin=true`.

- `GET /api/v1/admin/overview` — high-level user, game, analysis-job and session counts.
- `GET /api/v1/admin/users` — paginated user lookup with optional `q` filtering.
- `POST /api/v1/admin/users/{user_id}/suspend` — suspend an account, store a reason and revoke all refresh sessions.
- `POST /api/v1/admin/users/{user_id}/unsuspend` — restore access without restoring revoked sessions.

Suspended accounts cannot sign in and authenticated application endpoints reject their access tokens. Suspending an account revokes all persisted refresh sessions immediately.

## Abuse controls

Redis-backed authenticated rate limits protect expensive actions independently of the authentication rate limits:

- PGN imports: 20 per hour per user.
- Player relink/reanalysis: 30 per hour per user.
- Puzzle attempts: 120 per minute per user.

Production deployments should set `RATE_LIMIT_FAIL_OPEN=false` when Redis is operated as a required dependency.

## Audit trail

Administrative suspension, restoration and bootstrap grants are written to `audit_logs`. Suspension reasons are stored as metadata and on the user record for current-state inspection.
