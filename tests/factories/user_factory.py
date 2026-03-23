import uuid

from passlib.context import CryptContext

from api.db.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def build_user(
    email: str = "giuseppe.verdi@example.com",
    password: str = "Password1",
    name: str = "Giuseppe Verdi",
    role: str = "owner",
    email_verified: bool = True,
    tenant_id: uuid.UUID | None = None,
) -> User:
    """Build a User instance without persisting."""
    return User(
        email=email,
        password_hash=pwd_context.hash(password),
        name=name,
        role=role,
        email_verified=email_verified,
        tenant_id=tenant_id,
    )


def build_tenant_data(
    name: str = "Azienda Test SRL",
    type: str = "srl",
    regime_fiscale: str = "ordinario",
    piva: str = "12345678901",
) -> dict:
    """Build tenant data dict."""
    return {
        "name": name,
        "type": type,
        "regime_fiscale": regime_fiscale,
        "piva": piva,
    }
