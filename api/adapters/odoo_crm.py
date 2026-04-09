"""Odoo CRM adapter — JSON-RPC client per Odoo 18.

Gestisce pipeline commerciale, contatti, deal e ordini cliente.
L'adapter contabile resta in odoo.py (piano dei conti / registrazioni).

Il timesheet, le commesse e il billing restano sul sistema proprietario Nexa Data.
Odoo CRM gestisce SOLO: pipeline -> offerta -> ordine cliente -> conferma.
Quando l'ordine e confermato, il commerciale crea la commessa nel sistema Nexa Data.

Questo adapter e async e usa httpx, seguendo il pattern Salt Edge / FiscoAPI.
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from api.config import settings

logger = logging.getLogger(__name__)


# ── Dataclass di dominio ────────────────────────────────


@dataclass
class OdooCRMContact:
    id: int
    name: str
    email: str = ""
    phone: str = ""
    vat: str = ""
    street: str = ""
    city: str = ""
    zip_code: str = ""
    country: str = ""


@dataclass
class OdooCRMDeal:
    id: int
    name: str
    client_name: str = ""
    client_id: int = 0
    stage: str = ""
    stage_id: int = 0
    expected_revenue: float = 0.0
    probability: float = 0.0
    deal_type: str = ""       # T&M, fixed, spot, hardware
    daily_rate: float = 0.0
    estimated_days: float = 0.0
    technology: str = ""
    user_name: str = ""       # commerciale assegnato
    # Campi ordine cliente
    order_type: str = ""      # po, email, firma_word, portale
    order_reference: str = "" # numero PO / ODA / ref ordine
    order_date: str = ""      # data ricezione ordine
    order_notes: str = ""     # note specifiche processo cliente


@dataclass
class OdooCRMStage:
    id: int
    name: str
    sequence: int = 0


# ── Adapter ─────────────────────────────────────────────


class OdooCRMClient:
    """Client async JSON-RPC per il modulo CRM di Odoo 18.

    Usa le stesse credenziali di Odoo contabile ma espone
    un'interfaccia focalizzata su pipeline e contatti.
    """

    def __init__(
        self,
        url: str | None = None,
        db: str | None = None,
        user: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.url = (url or settings.odoo_url).rstrip("/")
        self.db = db or settings.odoo_db
        self.user = user or settings.odoo_user
        self.api_key = api_key or settings.odoo_api_key
        self.endpoint = f"{self.url}/jsonrpc"
        self._uid: int | None = None
        self._request_id = 0

    def is_configured(self) -> bool:
        """True se le credenziali Odoo CRM sono impostate."""
        return bool(self.url and self.db and self.user and self.api_key)

    # ── JSON-RPC core ───────────────────────────────────

    async def _call(self, service: str, method: str, args: list) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": args,
            },
            "id": self._request_id,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.endpoint, json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if "error" in result:
                err = result["error"]
                msg = err.get("data", {}).get("message", str(err))
                raise Exception(f"Odoo CRM error: {msg}")
            return result.get("result")

    async def authenticate(self) -> int:
        """Autentica e restituisce uid."""
        self._uid = await self._call(
            "common", "authenticate",
            [self.db, self.user, self.api_key, {}],
        )
        if not self._uid:
            raise Exception("Autenticazione Odoo CRM fallita.")
        logger.info("Odoo CRM autenticato, uid=%s", self._uid)
        return self._uid

    async def _execute(self, model: str, method: str, *args: Any) -> Any:
        if not self._uid:
            await self.authenticate()
        return await self._call(
            "object", "execute",
            [self.db, self._uid, self.api_key, model, method, *args],
        )

    async def search_read(
        self,
        model: str,
        domain: list | None = None,
        fields: list | None = None,
        limit: int = 0,
        order: str = "",
    ) -> list[dict]:
        domain = domain or []
        fields = fields or []
        kwargs: dict[str, Any] = {}
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return await self._execute(model, "search_read", domain, fields, **kwargs)

    async def create(self, model: str, vals: dict) -> int:
        return await self._execute(model, "create", vals)

    async def write(self, model: str, ids: list[int], vals: dict) -> bool:
        return await self._execute(model, "write", ids, vals)

    async def read(self, model: str, ids: list[int], fields: list | None = None) -> list[dict]:
        return await self._execute(model, "read", ids, fields or [])

    # ── Contatti (res.partner) ──────────────────────────

    async def get_contacts(
        self,
        domain: list | None = None,
        limit: int = 200,
    ) -> list[OdooCRMContact]:
        """Lista contatti aziendali da Odoo."""
        raw = await self.search_read(
            "res.partner",
            domain or [["is_company", "=", True]],
            ["id", "name", "email", "phone", "vat",
             "street", "city", "zip", "country_id"],
            limit=limit,
        )
        return [
            OdooCRMContact(
                id=r["id"],
                name=r["name"],
                email=r.get("email") or "",
                phone=r.get("phone") or "",
                vat=r.get("vat") or "",
                street=r.get("street") or "",
                city=r.get("city") or "",
                zip_code=r.get("zip") or "",
                country=r["country_id"][1] if r.get("country_id") else "",
            )
            for r in raw
        ]

    async def create_contact(
        self,
        name: str,
        email: str = "",
        vat: str = "",
        phone: str = "",
    ) -> int:
        vals: dict[str, Any] = {"name": name, "is_company": True}
        if email:
            vals["email"] = email
        if vat:
            vals["vat"] = vat
        if phone:
            vals["phone"] = phone
        return await self.create("res.partner", vals)

    # ── Pipeline / Deal (crm.lead) ─────────────────────

    async def get_deals(
        self,
        domain: list | None = None,
        limit: int = 100,
    ) -> list[OdooCRMDeal]:
        """Lista opportunita dalla pipeline."""
        raw = await self.search_read(
            "crm.lead",
            domain or [["type", "=", "opportunity"]],
            ["id", "name", "partner_id", "stage_id",
             "expected_revenue", "probability", "user_id",
             "x_deal_type", "x_daily_rate", "x_estimated_days",
             "x_technology", "x_order_type", "x_order_reference",
             "x_order_date", "x_order_notes"],
            limit=limit,
            order="create_date desc",
        )
        return [self._parse_deal(r) for r in raw]

    async def get_won_deals(self, since_date: str = "") -> list[OdooCRMDeal]:
        """Deal chiusi con successo (probability=100)."""
        domain: list = [["type", "=", "opportunity"], ["probability", "=", 100]]
        if since_date:
            domain.append(["write_date", ">=", since_date])
        raw = await self.search_read(
            "crm.lead", domain,
            ["id", "name", "partner_id", "expected_revenue",
             "x_deal_type", "x_daily_rate", "x_estimated_days",
             "x_technology", "write_date"],
        )
        return [self._parse_deal(r) for r in raw]

    async def create_deal(self, name: str, partner_id: int, **kwargs: Any) -> int:
        vals = {"name": name, "partner_id": partner_id, "type": "opportunity"}
        vals.update(kwargs)
        return await self.create("crm.lead", vals)

    async def update_deal(self, deal_id: int, vals: dict) -> bool:
        return await self.write("crm.lead", [deal_id], vals)

    async def get_stages(self) -> list[OdooCRMStage]:
        """Fasi della pipeline CRM."""
        raw = await self.search_read(
            "crm.stage", [], ["id", "name", "sequence"],
            order="sequence asc",
        )
        return [OdooCRMStage(id=r["id"], name=r["name"], sequence=r.get("sequence", 0))
                for r in raw]

    # ── Pipeline summary ────────────────────────────────

    async def get_pipeline_summary(self) -> dict:
        """Riepilogo pipeline: deal per fase + valore totale."""
        stages = await self.get_stages()
        deals = await self.get_deals(limit=500)

        by_stage: dict[str, dict] = {}
        for stage in stages:
            by_stage[stage.name] = {"count": 0, "value": 0.0}

        for deal in deals:
            stage_name = deal.stage or "Sconosciuto"
            if stage_name not in by_stage:
                by_stage[stage_name] = {"count": 0, "value": 0.0}
            by_stage[stage_name]["count"] += 1
            by_stage[stage_name]["value"] += deal.expected_revenue

        total_deals = len(deals)
        total_value = sum(d.expected_revenue for d in deals)

        return {
            "total_deals": total_deals,
            "total_value": total_value,
            "by_stage": by_stage,
        }

    # ── Ordine cliente ─────────────────────────────────

    async def register_order(
        self, deal_id: int,
        order_type: str,
        order_reference: str = "",
        order_notes: str = "",
    ) -> bool:
        """Registra l'ordine cliente su un deal.

        order_type: po | email | firma_word | portale
        """
        from datetime import date
        vals: dict[str, Any] = {
            "x_order_type": order_type,
            "x_order_date": date.today().isoformat(),
        }
        if order_reference:
            vals["x_order_reference"] = order_reference
        if order_notes:
            vals["x_order_notes"] = order_notes
        return await self.write("crm.lead", [deal_id], vals)

    async def get_pending_orders(self) -> list[OdooCRMDeal]:
        """Deal in fase 'Ordine Ricevuto' da confermare."""
        raw = await self.search_read(
            "crm.lead",
            [["type", "=", "opportunity"],
             ["x_order_type", "!=", False],
             ["probability", "<", 100]],
            ["id", "name", "partner_id", "expected_revenue",
             "x_deal_type", "x_order_type", "x_order_reference",
             "x_order_date", "x_order_notes", "stage_id"],
        )
        return [self._parse_deal(r) for r in raw]

    async def confirm_order(self, deal_id: int) -> bool:
        """Conferma l'ordine e sposta il deal in fase 'Confermato'.

        Dopo la conferma, il commerciale crea la commessa nel sistema Nexa Data.
        """
        stages = await self.get_stages()
        confirmed_stage = next(
            (s for s in stages if "confermat" in s.name.lower()),
            None,
        )
        vals: dict[str, Any] = {"probability": 100}
        if confirmed_stage:
            vals["stage_id"] = confirmed_stage.id
        return await self.write("crm.lead", [deal_id], vals)

    # ── Helper ──────────────────────────────────────────

    def _parse_deal(self, raw: dict) -> OdooCRMDeal:
        return OdooCRMDeal(
            id=raw["id"],
            name=raw.get("name", ""),
            client_name=raw["partner_id"][1] if raw.get("partner_id") else "",
            client_id=raw["partner_id"][0] if raw.get("partner_id") else 0,
            stage=raw["stage_id"][1] if raw.get("stage_id") else "",
            stage_id=raw["stage_id"][0] if raw.get("stage_id") else 0,
            expected_revenue=raw.get("expected_revenue", 0) or 0,
            probability=raw.get("probability", 0) or 0,
            deal_type=raw.get("x_deal_type") or "",
            daily_rate=raw.get("x_daily_rate") or 0,
            estimated_days=raw.get("x_estimated_days") or 0,
            technology=raw.get("x_technology") or "",
            user_name=raw["user_id"][1] if raw.get("user_id") else "",
            order_type=raw.get("x_order_type") or "",
            order_reference=raw.get("x_order_reference") or "",
            order_date=raw.get("x_order_date") or "",
            order_notes=raw.get("x_order_notes") or "",
        )
