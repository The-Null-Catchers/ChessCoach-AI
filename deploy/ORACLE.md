# Oracle production deployment

This deployment is designed to coexist with other applications on a small Oracle VM.

## Resource profile

- PostgreSQL: 1 GB / 0.5 CPU
- Redis: 256 MB / 0.2 CPU
- API: 768 MB / 0.5 CPU
- Celery + Stockfish: 3 GB / 1 CPU, concurrency 1
- Celery beat: 256 MB / 0.15 CPU
- Web: 768 MB / 0.4 CPU

The database and Redis are private to the Compose network. For initial IP-only testing, the web and API are exposed on host ports:

- Web: 3100
- API: 8100

When a real domain is available, prefer putting Caddy in front and binding these services back to loopback.

## First deploy

```bash
git clone https://github.com/The-Null-Catchers/ChessCoach-AI.git
cd ChessCoach-AI
cp .env.production.example .env.production
chmod 600 .env.production
```

Edit `.env.production` and replace every placeholder. Generate secrets with:

```bash
openssl rand -hex 32
openssl rand -base64 48
```

Then:

```bash
docker compose -f docker-compose.production.yml config
docker compose -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.production.yml ps
curl -fsS http://127.0.0.1:8100/health
curl -fsS http://127.0.0.1:8100/health/ready
```

## Remove later

Keep the volumes:

```bash
docker compose -f docker-compose.production.yml down
```

Delete ChessCoach data too:

```bash
docker compose -f docker-compose.production.yml down -v
```
