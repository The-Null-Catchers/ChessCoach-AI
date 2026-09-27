# Oracle production deployment

ChessCoach exposes the web client on port 3100 and keeps the backend bound to loopback on 8100.
The Next.js server proxies /api/v1/* to the backend over the Docker network. This means mobile
clients can temporarily use the same public web origin instead of exposing the API port directly.

## Public test URLs

- Web: http://82.70.209.175:3100
- API through web proxy: http://82.70.209.175:3100/api/v1
- Direct backend health from the server only: http://127.0.0.1:8100/health

## First deploy

```bash
git clone https://github.com/The-Null-Catchers/ChessCoach-AI.git
cd ChessCoach-AI
cp .env.production.example .env.production
chmod 600 .env.production
```

Edit .env.production and replace all secrets. Then:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml config
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
docker compose --env-file .env.production -f docker-compose.production.yml ps

curl -fsS http://127.0.0.1:8100/health
curl -fsS http://127.0.0.1:3100/health
```

The second health request verifies that the Next.js proxy can reach the backend.

## Update an existing server

```bash
cd ~/ChessCoach-AI
git fetch origin
git checkout main
git pull --ff-only origin main
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
docker compose --env-file .env.production -f docker-compose.production.yml ps
curl -fsS http://127.0.0.1:3100/health
```

## HTTPS later

Put Caddy in front of port 3100. The mobile API URL then becomes:

```
https://YOUR_CHESS_DOMAIN/api/v1
```

No public access to port 8100 is required.
