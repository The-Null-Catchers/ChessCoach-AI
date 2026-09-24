# Security

## Implemented controls

- Argon2 password hashing
- short-lived signed JWT access tokens
- persisted refresh-token sessions
- refresh-token rotation with hashed JTI storage
- refresh replay detection with family revocation
- logout and logout-all session invalidation
- authentication audit events
- one-time email verification and password-reset tokens stored only as SHA-256 hashes
- password reset revokes all active refresh sessions
- Redis-backed rate limiting for registration, login, verification and password reset
- asynchronous SMTP delivery for verification/reset emails through Celery
- per-user game and coaching authorization
- bounded PGN upload size
- isolated asynchronous analysis workers
- controlled CORS from configuration
- dependency-aware readiness checks that fail closed
- request IDs and structured request logging without query-string logging

## Production deployment requirements

- set a strong external `JWT_SECRET`; never use the development default
- store database, Redis and AI-provider credentials in a managed secret store
- terminate TLS at the ingress/reverse proxy
- restrict `CORS_ORIGINS` to the deployed first-party clients
- keep PostgreSQL and Redis private to the application network
- run API and workers as non-root containers/users where supported
- set upload/body limits at both reverse-proxy and application layers
- retain audit logs according to the deployment's privacy and incident-response policy

## Remaining security work

Before a public production launch, add:

- extend rate limiting beyond auth to import/analysis/admin endpoints
- CSRF controls if browser authentication moves to cookies
- deeper PGN/file content validation and abuse limits
- admin RBAC and privileged-action audit coverage
- dependency and secret scanning gates in CI
- security headers at the ingress/web layer
- documented backup, restore and key-rotation procedures
