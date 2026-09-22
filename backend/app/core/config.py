from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    app_name: str = 'ChessCoach AI'
    database_url: str = 'postgresql+psycopg://chesscoach:chesscoach@db:5432/chesscoach'
    redis_url: str = 'redis://redis:6379/0'
    jwt_secret: str = 'dev-only-change-me'
    jwt_algorithm: str = 'HS256'
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    stockfish_path: str = '/usr/games/stockfish'
    max_pgn_bytes: int = 10 * 1024 * 1024
    analysis_default_depth: int = 16


settings = Settings()
