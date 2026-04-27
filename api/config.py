
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

    # Super admin globali (operatori NexaData) — comma-separated email list
    # Es. SUPER_ADMIN_EMAILS=mgiurelli@nexadata.it,altro@nexadata.it
    super_admin_emails: str = ""

    @property
    def super_admin_emails_set(self) -> set[str]:
        return {e.strip().lower() for e in self.super_admin_emails.split(",") if e.strip()}

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

    # A-Cube Open Banking (AISP) — ADR-012
    acube_ob_env: str = "sandbox"  # sandbox | production
    acube_ob_login_email: str = ""
    acube_ob_login_password: str = ""
    acube_ob_login_url_sandbox: str = "https://common-sandbox.api.acubeapi.com/login"
    acube_ob_login_url_prod: str = "https://common.api.acubeapi.com/login"
    acube_ob_base_url_sandbox: str = "https://ob-sandbox.api.acubeapi.com"
    acube_ob_base_url_prod: str = "https://ob.api.acubeapi.com"
    acube_ob_webhook_secret: str = ""  # chiave HMAC verifica webhook (da A-Cube, TBD)
    acube_ob_webhook_verify_signature: bool = False  # false in sandbox finché A-Cube non ci dà la chiave reale
    acube_ob_webhook_signature_header: str = "X-Acube-Signature"  # da confermare ticket 05
    acube_ob_webhook_signature_algo: str = "sha256"  # hmac-sha256 (ipotesi più comune)
    acube_ob_webhook_signature_prefix: str = ""  # es. "sha256=" (Stripe-style); vuoto se firma hex puro
    acube_ob_webhook_max_age_seconds: int = 300  # replay protection: rifiuta eventi più vecchi di 5 min

    # A-Cube E-Invoicing Italy (SDI send/receive + Cassetto Fiscale bulk download)
    # Shared JWT auth with AISP (same account).
    acube_einvoicing_base_url_sandbox: str = "https://api-sandbox.acubeapi.com"
    acube_einvoicing_base_url_prod: str = "https://api.acubeapi.com"
    # Optional override: separate env for e-invoicing vs AISP.
    # Use case: AISP in production while e-invoicing still in sandbox (waiting A-Cube provisioning).
    # Empty value = falls back to acube_ob_env.
    acube_einvoicing_env: str = ""
    # Optional separate credentials for prod (sandbox + prod accounts can differ).
    # Empty = use acube_ob_login_email / acube_ob_login_password.
    acube_prod_login_email: str = ""
    acube_prod_login_password: str = ""
    email_from: str = "AgentFlow <noreply@nexadata.it>"

    app_name: str = "AgentFlow"
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-6"

    aes_key: str = "change-me-32-bytes-hex-encoded-key"

    # Odoo CRM
    odoo_url: str = ""  # es. https://nexadata.odoo.com
    odoo_db: str = ""  # nome database Odoo
    odoo_user: str = ""  # email utente Odoo
    odoo_api_key: str = ""  # API key (Preferenze > Sicurezza)
    odoo_webhook_secret: str = ""  # secret per validare webhook in ingresso

    # Brute force protection
    max_login_attempts: int = 5
    lockout_minutes: int = 15

    # Password reset
    password_reset_expire_minutes: int = 60

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
