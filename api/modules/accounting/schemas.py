from pydantic import BaseModel


class AccountItem(BaseModel):
    code: str
    name: str
    account_type: str


class PianoContiResponse(BaseModel):
    db_name: str
    tipo_azienda: str
    regime_fiscale: str
    accounts: list[AccountItem]
    journals: list[str]
    tax_codes: list[str]
    note: str | None = None


class PianoContiCreateRequest(BaseModel):
    """Explicit request to create/recreate piano conti."""
    force: bool = False  # Force recreation if already exists


class MessageResponse(BaseModel):
    message: str
