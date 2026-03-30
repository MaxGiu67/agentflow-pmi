import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt as _bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db.models import User

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC time without timezone info (for TIMESTAMP WITHOUT TIME ZONE)."""
    return datetime.now(UTC).replace(tzinfo=None)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _hash_password(self, password: str) -> str:
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    def _create_access_token(self, user_id: uuid.UUID, email: str) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def _create_refresh_token(self, user_id: uuid.UUID) -> str:
        expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def register(self, email: str, password: str, name: str | None = None) -> User:
        existing = await self._get_user_by_email(email)
        if existing:
            raise ValueError("Email gia registrata")

        verification_token = secrets.token_urlsafe(32)
        user = User(
            email=email,
            password_hash=self._hash_password(password),
            name=name,
            role="owner",
            email_verified=False,
            verification_token=verification_token,
        )
        self.db.add(user)
        await self.db.flush()

        await self._send_verification_email(user.email, verification_token)

        logger.info("User registered: %s", email)
        return user

    async def _send_verification_email(self, email: str, token: str) -> None:
        from api.adapters.email import send_verification_email
        await send_verification_email(email, token)

    async def verify_email(self, token: str) -> User:
        result = await self.db.execute(
            select(User).where(User.verification_token == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("Token di verifica non valido")

        user.email_verified = True
        user.verification_token = None
        await self.db.flush()

        logger.info("Email verified: %s", user.email)
        return user

    async def login(self, email: str, password: str) -> dict:
        user = await self._get_user_by_email(email)
        if not user:
            raise ValueError("Credenziali non valide")

        # Check lockout
        if user.locked_until and user.locked_until > _utcnow():
            remaining = int((user.locked_until - _utcnow()).total_seconds() / 60) + 1
            raise ValueError(
                f"Account bloccato per troppi tentativi. Riprova tra {remaining} minuti"
            )

        # Reset lockout if expired
        if user.locked_until and user.locked_until <= _utcnow():
            user.failed_login_attempts = 0
            user.locked_until = None

        if not self._verify_password(password, user.password_hash):
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= settings.max_login_attempts:
                user.locked_until = _utcnow() + timedelta(minutes=settings.lockout_minutes)
                await self.db.flush()
                logger.warning("Account locked due to brute force: %s", email)
                await self._send_lockout_notification(email)
                raise ValueError(
                    f"Account bloccato per {settings.lockout_minutes} minuti dopo "
                    f"{settings.max_login_attempts} tentativi falliti"
                )

            await self.db.flush()
            raise ValueError("Credenziali non valide")

        if not user.email_verified:
            raise ValueError("Email non verificata. Controlla la tua casella email")

        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.flush()

        access_token = self._create_access_token(user.id, user.email)
        refresh_token = self._create_refresh_token(user.id)

        logger.info("User logged in: %s", email)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
        }

    async def _send_lockout_notification(self, email: str) -> None:
        from api.adapters.email import send_lockout_notification
        await send_lockout_notification(email)

    async def refresh_token(self, refresh_token_str: str) -> dict:
        try:
            payload = jwt.decode(
                refresh_token_str, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
        except JWTError as e:
            raise ValueError("Refresh token non valido") from e

        if payload.get("type") != "refresh":
            raise ValueError("Token non di tipo refresh")

        user_id = uuid.UUID(payload["sub"])
        user = await self._get_user_by_id(user_id)
        if not user:
            raise ValueError("Utente non trovato")

        access_token = self._create_access_token(user.id, user.email)
        new_refresh = self._create_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
        }

    async def request_password_reset(self, email: str) -> None:
        user = await self._get_user_by_email(email)
        # Always return success to avoid email enumeration
        if not user:
            return

        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        user.password_reset_expires = _utcnow() + timedelta(
            minutes=settings.password_reset_expire_minutes
        )
        await self.db.flush()

        await self._send_password_reset_email(email, reset_token)

    async def _send_password_reset_email(self, email: str, token: str) -> None:
        from api.adapters.email import send_password_reset_email
        await send_password_reset_email(email, token)

    async def reset_password(self, token: str, new_password: str) -> None:
        result = await self.db.execute(
            select(User).where(User.password_reset_token == token)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("Token di reset non valido")

        if user.password_reset_expires and user.password_reset_expires < _utcnow():
            raise ValueError("Token di reset scaduto")

        user.password_hash = self._hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.flush()

        logger.info("Password reset successful for: %s", user.email)

    def decode_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
        except JWTError as e:
            raise ValueError("Token non valido") from e

        if payload.get("type") != "access":
            raise ValueError("Token non di tipo access")

        return payload
