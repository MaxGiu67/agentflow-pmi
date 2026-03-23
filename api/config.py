from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://contabot:contabot@localhost:5432/contabot"
    database_url_sync: str = "postgresql://contabot:contabot@localhost:5432/contabot"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24h
    jwt_refresh_token_expire_days: int = 7

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@contabot.it"

    app_name: str = "ContaBot"
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    aes_key: str = "change-me-32-bytes-hex-encoded-key"

    # Brute force protection
    max_login_attempts: int = 5
    lockout_minutes: int = 15

    # Password reset
    password_reset_expire_minutes: int = 60

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
