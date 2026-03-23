import uuid

import bcrypt as _bcrypt

from api.db.models import User


def _hash_pw(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


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
        password_hash=_hash_pw(password),
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
