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
    is_super_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileChangeWarning(BaseModel):
    message: str
    requires_confirmation: bool
    affected_areas: list[str]


# ── Impostazioni Fatturazione (US-42) ──


class InvoiceSettingsRequest(BaseModel):
    """Settings for invoice generation — saved in Tenant, reused for every invoice."""
    # Sede
    sede_indirizzo: str | None = None
    sede_numero_civico: str | None = None
    sede_cap: str | None = None
    sede_comune: str | None = None
    sede_provincia: str | None = None
    sede_nazione: str | None = "IT"

    # Anagrafica
    codice_fiscale: str | None = None
    regime_fiscale_sdi: str | None = None  # RF01-RF19

    # Pagamento
    iban: str | None = None
    banca_nome: str | None = None
    bic: str | None = None
    modalita_pagamento: str | None = None  # MP01-MP23
    condizioni_pagamento: str | None = None  # TP01-TP03
    giorni_pagamento: int | None = None

    # REA (società)
    rea_ufficio: str | None = None
    rea_numero: str | None = None
    rea_capitale_sociale: float | None = None
    rea_socio_unico: str | None = None  # SU/SM
    rea_stato_liquidazione: str | None = None  # LN/LS

    # Contatti
    telefono: str | None = None
    email_aziendale: str | None = None
    pec: str | None = None

    @field_validator("regime_fiscale_sdi")
    @classmethod
    def check_regime_sdi(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = [f"RF{i:02d}" for i in range(1, 20)]
        if v not in valid:
            raise ValueError(f"Regime fiscale SDI non valido: {v}. Valori: RF01-RF19")
        return v

    @field_validator("modalita_pagamento")
    @classmethod
    def check_modalita(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = [f"MP{i:02d}" for i in range(1, 24)]
        if v not in valid:
            raise ValueError(f"Modalità pagamento non valida: {v}. Valori: MP01-MP23")
        return v

    @field_validator("condizioni_pagamento")
    @classmethod
    def check_condizioni(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("TP01", "TP02", "TP03"):
            raise ValueError(f"Condizioni pagamento non valide: {v}. Valori: TP01, TP02, TP03")
        return v

    @field_validator("iban")
    @classmethod
    def check_iban(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.replace(" ", "").upper()
        if len(v) < 15 or len(v) > 34:
            raise ValueError("IBAN non valido: lunghezza non corretta")
        return v


class InvoiceSettingsResponse(BaseModel):
    """Current invoice settings from Tenant."""
    # Azienda
    name: str | None = None
    piva: str | None = None
    codice_fiscale: str | None = None
    regime_fiscale_sdi: str | None = None

    # Sede
    sede_indirizzo: str | None = None
    sede_numero_civico: str | None = None
    sede_cap: str | None = None
    sede_comune: str | None = None
    sede_provincia: str | None = None
    sede_nazione: str | None = None

    # Pagamento
    iban: str | None = None
    banca_nome: str | None = None
    bic: str | None = None
    modalita_pagamento: str | None = None
    condizioni_pagamento: str | None = None
    giorni_pagamento: int | None = None

    # REA
    rea_ufficio: str | None = None
    rea_numero: str | None = None
    rea_capitale_sociale: float | None = None
    rea_socio_unico: str | None = None
    rea_stato_liquidazione: str | None = None

    # Contatti
    telefono: str | None = None
    email_aziendale: str | None = None
    pec: str | None = None

    model_config = {"from_attributes": True}
