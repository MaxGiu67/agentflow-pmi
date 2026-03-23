import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La password deve avere almeno 8 caratteri")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La password deve contenere almeno una lettera maiuscola")
        if not re.search(r"[0-9]", v):
            raise ValueError("La password deve contenere almeno un numero")
        return v


class RegisterResponse(BaseModel):
    id: uuid.UUID
    email: str
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La password deve avere almeno 8 caratteri")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La password deve contenere almeno una lettera maiuscola")
        if not re.search(r"[0-9]", v):
            raise ValueError("La password deve contenere almeno un numero")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
