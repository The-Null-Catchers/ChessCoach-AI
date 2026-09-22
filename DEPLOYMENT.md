# Deployment

Build API and worker from `backend/Dockerfile`; run them as separate services. Use managed PostgreSQL/Redis where possible. Keep Stockfish execution in worker containers with explicit CPU/memory limits. The Next.js app is independently deployable. Mobile releases are produced by CI; production signing secrets must remain in GitHub Actions secrets or a secure signing service.
