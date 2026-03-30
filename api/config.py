
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://contabot:contabot@localhost:5432/contabot"

    @property
    def async_database_url(self) -> str:
        """Return asyncpg-compatible URL, converting Railway's postgresql:// if needed."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24h
    jwt_refresh_token_expire_days: int = 7

    resend_api_key: str = ""
    fiscoapi_secret_key: str = ""
    fiscoapi_base_url: str = "https://api.fiscoapi.com/api_esterne"
    fiscoapi_link_code: str = ""  # codice link FiscoAPI (es. vRMMZPep55Q)

    saltedge_app_id: str = ""
    saltedge_secret: str = ""
    saltedge_base_url: str = "https://www.saltedge.com/api/v6"
    email_from: str = "AgentFlow <noreply@nexadata.it>"

    app_name: str = "AgentFlow"
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-6"

    aes_key: str = "change-me-32-bytes-hex-encoded-key"

    # Brute force protection
    max_login_attempts: int = 5
    lockout_minutes: int = 15

    # Password reset
    password_reset_expire_minutes: int = 60

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
