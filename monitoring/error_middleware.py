"""FastAPI middleware errore — drop-in per Monitoring Agent.

Setup nel progetto target:
    from monitoring.error_middleware import ErrorTrackingMiddleware
    app.add_middleware(ErrorTrackingMiddleware)

Env vars:
    MONITORING_HUB_URL=https://monitoring-hub-api-production.up.railway.app
    MONITORING_PROJECT_ID=<slug>
    MONITORING_HMAC_SECRET=<48 byte random>
    MONITORING_DISABLE_PII_REDACT=1   # opt-out (default ON)
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import time
import traceback
import uuid
from pathlib import Path

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

log = logging.getLogger(__name__)

HUB_URL = os.environ.get("MONITORING_HUB_URL", "")
PROJECT_ID = os.environ.get("MONITORING_PROJECT_ID", "")
HMAC_SECRET = os.environ.get("MONITORING_HMAC_SECRET", "")
PII_REDACT = os.environ.get("MONITORING_DISABLE_PII_REDACT") != "1"
BUFFER_PATH = Path(os.environ.get("MONITORING_BUFFER_PATH", "./monitoring_buffer.jsonl"))

# Pattern PII (ADR-018)
PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b"), "[JWT]"),
]


def _redact(text: str) -> str:
    if not PII_REDACT or not text:
        return text
    for pattern, repl in PII_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _serialize_exception(exc: BaseException) -> dict:
    tb = traceback.extract_tb(exc.__traceback__)
    file_path = tb[-1].filename if tb else None
    line_number = tb[-1].lineno if tb else None
    error_type = type(exc).__name__
    stack = _redact(traceback.format_exc())[:8000]
    return {
        "error_type": error_type,
        "message": _redact(str(exc))[:4000],
        "stack": stack,
        "file_path": file_path,
        "line_number": line_number,
    }


async def _send_to_hub(payload: dict) -> bool:
    """POST /events con HMAC + retry exp backoff. Buffer locale on fail."""
    if not HUB_URL or not PROJECT_ID or not HMAC_SECRET:
        log.warning("monitoring_disabled", extra={"reason": "missing env vars"})
        return False

    body = json.dumps(payload).encode()
    sig = _sign(body, HMAC_SECRET)
    headers = {"X-Signature": f"sha256={sig}", "Content-Type": "application/json"}

    backoff = 1.0
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.post(f"{HUB_URL}/api/v1/events", content=body, headers=headers)
                if r.status_code in (200, 201, 202):
                    return True
                if r.status_code in (401, 413, 422):
                    log.warning("monitoring_rejected", extra={"status": r.status_code, "body": r.text[:200]})
                    return False
        except Exception as e:
            log.warning("monitoring_send_failed", extra={"attempt": attempt, "error": str(e)})
        await asyncio.sleep(backoff)
        backoff *= 2

    # Buffer locale fallback
    try:
        with BUFFER_PATH.open("a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        log.error("buffer_write_failed", extra={"error": str(e)})
    return False


def _build_payload(
    request: Request, exc: BaseException, severity: str = "CRITICAL"
) -> dict:
    err = _serialize_exception(exc)
    return {
        "event_id": str(uuid.uuid4()),
        "project_id": PROJECT_ID,
        "service_id": os.environ.get("MONITORING_SERVICE_ID", "api"),
        "severity": severity,
        "error_type": err["error_type"],
        "message": err["message"],
        "stack": err["stack"],
        "file_path": err["file_path"],
        "line_number": err["line_number"],
        "request_path": str(request.url.path),
        "request_method": request.method,
        "metadata": {
            "user_agent": _redact(request.headers.get("user-agent", ""))[:200],
        },
        "source": "middleware:fastapi",
        "timestamp": time.time(),
    }


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            # Filter: solo uncaught (non HTTPException 4xx attese)
            from fastapi.exceptions import HTTPException as FastAPIHTTPException

            if isinstance(exc, FastAPIHTTPException) and 400 <= exc.status_code < 500:
                raise

            # Fire-and-forget al hub (non bloccante)
            payload = _build_payload(request, exc, severity="CRITICAL")
            asyncio.create_task(_send_to_hub(payload))

            # Re-raise per il chain handler standard
            raise
