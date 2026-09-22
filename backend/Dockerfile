FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends stockfish && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini pyproject.toml entrypoint.sh ./
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
