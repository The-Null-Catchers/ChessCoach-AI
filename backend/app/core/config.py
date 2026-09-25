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
    cors_origins: str = 'http://localhost:3000'
    ai_provider: str = 'template'
    ai_model: str = 'deterministic-v1'
    ai_base_url: str = 'https://api.openai.com/v1'
    ai_api_key: str = ''
    auth_action_token_minutes: int = 30
    rate_limit_enabled: bool = True
    rate_limit_fail_open: bool = True
    admin_emails: str = ''
    frontend_url: str = 'http://localhost:3000'
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_username: str = ''
    smtp_password: str = ''
    smtp_from_email: str = 'noreply@chesscoach.local'
    smtp_starttls: bool = True


settings = Settings()
