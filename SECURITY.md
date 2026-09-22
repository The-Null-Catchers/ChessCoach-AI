# Security

Current foundations: Argon2 password hashing, signed short-lived access tokens, per-user game authorization, bounded PGN upload size and isolated workers.

Before production: persist hashed refresh-token families with rotation/reuse detection; email verification/reset flows; rate limiting; strict CORS; CSRF controls for browser cookie flows; file content validation; secret manager integration; audit events; dependency/secret scanning; admin RBAC and abuse controls.
