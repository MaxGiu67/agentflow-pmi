"""PEC (Posta Elettronica Certificata) client — multi-provider SMTP/IMAP.

Supports major Italian PEC providers: Aruba, Namirial, Poste, Legalmail (InfoCert).
Uses standard SMTP/IMAP so works with every certified PEC provider.

Reference:
- SDI PEC address for inbound invoices: sdi01@pec.fatturapa.it
- SDI responses come from servizisdi@pec.fatturapa.it
- Receipt types: RC (ricevuta consegna), NS (notifica scarto), MC (mancata consegna),
  NE (notifica esito committente), DT (decorrenza termini), AT (attestazione trasmissione)
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Any

logger = logging.getLogger(__name__)


# Preset server SMTP/IMAP per provider (porte SSL standard)
PEC_PROVIDERS: dict[str, dict[str, Any]] = {
    "aruba": {
        "label": "Aruba PEC",
        "smtp_host": "smtps.pec.aruba.it",
        "smtp_port": 465,
        "imap_host": "imaps.pec.aruba.it",
        "imap_port": 993,
        "docs": "https://guide.pec.it/configurazione-parametri-server-pec.aspx",
    },
    "namirial": {
        "label": "Namirial (Sicurezzapostale)",
        "smtp_host": "sendm.pec.it",
        "smtp_port": 465,
        "imap_host": "mbox.pec.it",
        "imap_port": 993,
        "docs": "https://www.sicurezzapostale.it/guida/",
    },
    "poste": {
        "label": "Poste Italiane PEC",
        "smtp_host": "relay.poste.it",
        "smtp_port": 465,
        "imap_host": "mail.postecert.it",
        "imap_port": 993,
        "docs": "https://www.poste.it/postecert-supporto.html",
    },
    "legalmail": {
        "label": "Legalmail (InfoCert)",
        "smtp_host": "sendm.cert.legalmail.it",
        "smtp_port": 465,
        "imap_host": "mbox.cert.legalmail.it",
        "imap_port": 993,
        "docs": "https://www.legalmail.it/assistenza/",
    },
    "register": {
        "label": "Register.it PEC",
        "smtp_host": "smtps.pec.register.it",
        "smtp_port": 465,
        "imap_host": "imaps.pec.register.it",
        "imap_port": 993,
        "docs": "https://we.register.it/supporto-pec.html",
    },
}

SDI_PEC_ADDRESS = "sdi01@pec.fatturapa.it"
SDI_PEC_SENDER = "servizisdi@pec.fatturapa.it"
SDI_RECEIPT_PREFIXES = ("RC", "NS", "MC", "NE", "DT", "AT", "EC", "SE")


@dataclass
class PecTestResult:
    smtp_ok: bool
    imap_ok: bool
    error: str | None = None


@dataclass
class PecSendResult:
    message_id: str
    sent_at: datetime
    recipient: str


@dataclass
class PecReceipt:
    message_id: str
    subject: str
    sender: str
    receipt_type: str  # RC|NS|MC|NE|DT|AT|EC|SE
    related_filename: str | None  # file fattura originale (es. IT12345678901_00001.xml)
    received_at: datetime
    raw_headers: str


def get_provider_preset(provider: str) -> dict[str, Any] | None:
    """Return SMTP/IMAP preset for a known provider, or None for custom."""
    return PEC_PROVIDERS.get(provider.lower())


def test_connection(
    smtp_host: str,
    smtp_port: int,
    imap_host: str,
    imap_port: int,
    username: str,
    password: str,
) -> PecTestResult:
    """Verify SMTP + IMAP credentials. Synchronous — call via asyncio.to_thread in async code."""
    ctx = ssl.create_default_context()
    smtp_ok = False
    imap_ok = False
    last_err: str | None = None

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=15) as smtp:
            smtp.login(username, password)
            smtp_ok = True
    except Exception as e:
        last_err = f"SMTP: {type(e).__name__}: {e}"
        logger.warning("PEC SMTP test failed: %s", last_err)

    try:
        with imaplib.IMAP4_SSL(imap_host, imap_port, ssl_context=ctx, timeout=15) as imap:
            imap.login(username, password)
            imap.select("INBOX", readonly=True)
            imap.logout()
            imap_ok = True
    except Exception as e:
        last_err = (last_err + " | " if last_err else "") + f"IMAP: {type(e).__name__}: {e}"
        logger.warning("PEC IMAP test failed: %s", last_err)

    return PecTestResult(smtp_ok=smtp_ok, imap_ok=imap_ok, error=last_err)


def send_signed_invoice(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    from_address: str,
    filename: str,
    p7m_content: bytes,
    recipient: str = SDI_PEC_ADDRESS,
    subject: str | None = None,
    body_text: str | None = None,
) -> PecSendResult:
    """Send a signed FatturaPA (.xml.p7m) to SDI via PEC. Synchronous.

    Args:
        filename: must match pattern IT{piva}_{progressive}.xml.p7m
        p7m_content: raw bytes of the signed .p7m file
        recipient: defaults to SDI PEC address
    """
    if not filename.endswith(".p7m") and not filename.endswith(".xml"):
        raise ValueError("Il file allegato deve essere .xml o .xml.p7m (firmato CAdES)")

    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = recipient
    msg["Date"] = formatdate(localtime=True)
    msg_id = make_msgid(domain=from_address.split("@")[-1])
    msg["Message-ID"] = msg_id
    msg["Subject"] = subject or f"Invio fattura {filename}"

    body = body_text or (
        "In allegato fattura elettronica firmata destinata al Sistema di Interscambio.\n"
        "Inviata da AgentFlow PMI."
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    part = MIMEApplication(p7m_content, _subtype="pkcs7-mime" if filename.endswith(".p7m") else "xml")
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=30) as smtp:
        smtp.login(username, password)
        smtp.send_message(msg)

    return PecSendResult(message_id=msg_id, sent_at=datetime.utcnow(), recipient=recipient)


_RECEIPT_FILENAME_RE = re.compile(
    r"(?P<prefix>RC|NS|MC|NE|DT|AT|EC|SE)_(?P<original>IT[0-9A-Z]+_[0-9A-Z]+)(?:_\d+)?\.xml",
    re.IGNORECASE,
)


def poll_receipts(
    imap_host: str,
    imap_port: int,
    username: str,
    password: str,
    since_date: datetime | None = None,
    limit: int = 50,
) -> list[PecReceipt]:
    """Poll PEC inbox for SDI receipts. Synchronous.

    Filters messages from SDI sender (servizisdi@pec.fatturapa.it) and parses the
    receipt type from the attachment filename (RC_, NS_, MC_, NE_, DT_, AT_, EC_, SE_).
    """
    ctx = ssl.create_default_context()
    receipts: list[PecReceipt] = []

    with imaplib.IMAP4_SSL(imap_host, imap_port, ssl_context=ctx, timeout=30) as imap:
        imap.login(username, password)
        imap.select("INBOX")

        # SDI response messages come from servizisdi@pec.fatturapa.it (or the official notary PEC).
        search_criteria = '(FROM "pec.fatturapa.it")'
        if since_date:
            search_criteria = f'({search_criteria} SINCE "{since_date.strftime("%d-%b-%Y")}")'

        typ, data = imap.search(None, search_criteria)
        if typ != "OK":
            return receipts

        ids = data[0].split()
        for num in ids[-limit:]:
            typ, msg_data = imap.fetch(num, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            parsed = email.message_from_bytes(raw)
            receipt = _parse_receipt_message(parsed)
            if receipt:
                receipts.append(receipt)

    return receipts


def _parse_receipt_message(msg) -> PecReceipt | None:
    """Extract SDI receipt info from a parsed email.message.Message."""
    subject = msg.get("Subject", "") or ""
    sender = msg.get("From", "") or ""
    message_id = msg.get("Message-ID", "") or ""

    # scan attachments for the receipt filename pattern
    receipt_type = None
    related_filename = None
    for part in msg.walk():
        disp = part.get("Content-Disposition", "") or ""
        if "attachment" not in disp.lower():
            continue
        fname = part.get_filename() or ""
        m = _RECEIPT_FILENAME_RE.search(fname)
        if m:
            receipt_type = m.group("prefix").upper()
            related_filename = m.group("original") + ".xml"
            break

    if not receipt_type:
        # Also check subject line for receipt markers
        for p in SDI_RECEIPT_PREFIXES:
            if subject.upper().startswith(p + " "):
                receipt_type = p
                break
        if not receipt_type:
            return None

    return PecReceipt(
        message_id=message_id,
        subject=subject[:500],
        sender=sender[:255],
        receipt_type=receipt_type,
        related_filename=related_filename,
        received_at=datetime.utcnow(),
        raw_headers="\n".join(f"{k}: {v}" for k, v in msg.items())[:4000],
    )
