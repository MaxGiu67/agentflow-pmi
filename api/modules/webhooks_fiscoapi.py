"""Webhook endpoint for FiscoAPI callbacks.

FiscoAPI sends updates when:
- Session state changes (SPID login progress)
- Invoice request completes
- F24/CU data is ready
"""

import logging

from fastapi import APIRouter, Request
from api.adapters.fiscoapi_real import FiscoAPIReal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/fiscoapi")
async def fiscoapi_webhook(request: Request) -> dict:
    """Receive FiscoAPI webhook notifications."""
    payload = await request.json()
    parsed = FiscoAPIReal.parse_webhook(payload)

    logger.info(
        "FiscoAPI webhook: type=%s event=%s",
        parsed["type"],
        parsed["event"],
    )

    tipo = parsed["type"]
    data = parsed["data"]

    if tipo == "Sessione":
        stato = data.get("stato", "")
        logger.info("Session update: %s", stato)
        if stato == "sessione_attiva":
            logger.info("SPID authentication completed! Session is active.")
        elif stato in ("sessione_in_errore", "sessione_scaduta", "credenziali_errate"):
            logger.warning("SPID session failed: %s", stato)

    elif tipo == "RichiestaFatture":
        stato = data.get("stato", "")
        n_fatture = data.get("totale_fatture", 0)
        logger.info("Invoice request update: stato=%s fatture=%s", stato, n_fatture)
        if stato == "completata":
            logger.info("Invoices ready! Total: %s", n_fatture)

    elif tipo == "RichiestaVersamenti":
        logger.info("Payments (F24/F23) data update: %s", data.get("stato"))

    elif tipo == "RichiestaCertificazioneUnica":
        logger.info("CU data update: %s", data.get("stato"))

    else:
        logger.info("Unknown webhook type: %s — data: %s", tipo, data)

    return {"status": "ok", "type": tipo}
