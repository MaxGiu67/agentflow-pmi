"""Verifica firma HMAC per webhook (A-Cube, Brevo, Portal, ecc.).

Riusabile — parametrizzato per algoritmo, nome header, prefisso, payload canonico.

Design principles:
- `hmac.compare_digest` → constant-time comparison (no timing attack)
- Body **raw** letto prima di parsing JSON (ordine byte critico per HMAC)
- Replay protection opzionale via timestamp check
- Nessun log del secret (solo prefisso/suffisso mascherato se serve)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class InvalidSignatureError(Exception):
    """Firma webhook invalida o mancante."""


class ReplayAttackError(Exception):
    """Evento troppo vecchio — possibile replay attack."""


@dataclass(frozen=True)
class SignatureConfig:
    """Configurazione verifica firma per un provider webhook."""

    header_name: str
    secret: str
    algorithm: str = "sha256"  # sha256 | sha512
    prefix: str = ""            # es. "sha256=" (Stripe-style), vuoto per firma hex pura
    max_age_seconds: int | None = None  # None = disabilita replay check
    timestamp_header: str | None = None  # es. "X-Timestamp" — richiesto se max_age_seconds != None


def compute_signature(body: bytes, config: SignatureConfig) -> str:
    """Calcola la firma HMAC del body usando la config fornita.

    Ritorna la firma formattata con eventual prefix (es. 'sha256=abc...').
    """
    if not hasattr(hashlib, config.algorithm):
        raise ValueError(f"Algoritmo HMAC non supportato: {config.algorithm}")

    digest = hmac.new(
        config.secret.encode("utf-8"),
        body,
        getattr(hashlib, config.algorithm),
    ).hexdigest()

    return f"{config.prefix}{digest}" if config.prefix else digest


def verify_signature(
    body: bytes,
    received_signature: str | None,
    config: SignatureConfig,
    received_timestamp: str | None = None,
) -> None:
    """Verifica la firma di un webhook.

    Args:
        body: request body raw (bytes)
        received_signature: valore dell'header firma (None se assente)
        config: SignatureConfig del provider
        received_timestamp: valore dell'header timestamp (per replay check)

    Raises:
        InvalidSignatureError: firma assente, formato errato, o non combacia
        ReplayAttackError: timestamp troppo vecchio (se max_age_seconds attivo)
    """
    if not config.secret:
        raise InvalidSignatureError(
            "Secret non configurato per la verifica firma webhook"
        )

    if not received_signature:
        raise InvalidSignatureError(
            f"Header firma mancante: {config.header_name}"
        )

    # Replay protection
    if config.max_age_seconds is not None:
        if not received_timestamp:
            raise InvalidSignatureError(
                f"Header timestamp mancante: {config.timestamp_header}"
            )
        try:
            ts = int(received_timestamp)
        except (TypeError, ValueError):
            raise InvalidSignatureError("Timestamp non numerico")
        now = int(time.time())
        age = now - ts
        if age > config.max_age_seconds:
            raise ReplayAttackError(
                f"Evento troppo vecchio ({age}s > {config.max_age_seconds}s)"
            )
        if age < -60:  # clock drift tollerato max 60s
            raise ReplayAttackError(f"Evento dal futuro ({age}s)")

    expected = compute_signature(body, config)

    # Constant-time comparison (hmac.compare_digest)
    if not hmac.compare_digest(expected, received_signature):
        logger.warning(
            "Firma webhook non combacia (provider=%s, header=%s)",
            config.algorithm,
            config.header_name,
        )
        raise InvalidSignatureError("Firma non valida")
