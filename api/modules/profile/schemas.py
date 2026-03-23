import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_validator

from api.utils.validators import validate_ateco, validate_piva


class TipoAzienda(str, Enum):
    srl = "srl"
    srls = "srls"
    piva = "piva"
    ditta_individuale = "ditta_individuale"
    altro = "altro"


class RegimeFiscale(str, Enum):
    forfettario = "forfettario"
    semplificato = "semplificato"
    ordinario = "ordinario"


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    tipo_azienda: TipoAzienda | None = None
    regime_fiscale: RegimeFiscale | None = None
    piva: str | None = None
    codice_ateco: str | None = None
    azienda_nome: str | None = None

    @field_validator("piva")
    @classmethod
    def check_piva(cls, v: str | None) -> str | None:
        if v is None:
            return v
        is_valid, error = validate_piva(v)
        if not is_valid:
            raise ValueError(error)
        return v

    @field_validator("codice_ateco")
    @classmethod
    def check_ateco(cls, v: str | None) -> str | None:
        if v is None:
            return v
        is_valid, error = validate_ateco(v)
        if not is_valid:
            raise ValueError(error)
        return v


class ProfileResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str | None
    role: str
    tenant_id: uuid.UUID | None
    azienda_nome: str | None = None
    tipo_azienda: str | None = None
    regime_fiscale: str | None = None
    piva: str | None = None
    codice_ateco: str | None = None
    has_piano_conti: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileChangeWarning(BaseModel):
    message: str
    requires_confirmation: bool
    affected_areas: list[str]
