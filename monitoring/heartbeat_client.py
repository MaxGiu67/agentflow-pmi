"""Heartbeat client Python (web 60s + worker 30s) — drop-in.

Setup:
    from monitoring.heartbeat_client import HeartbeatClient
    HeartbeatClient.start_web()    # 60s, retry standard
    HeartbeatClient.start_worker(service_id="worker:main")  # 30s, retry aggressivo
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
import uuid
from typing import Optional

import httpx

log = logging.getLogger(__name__)

HUB_URL = os.environ.get("MONITORING_HUB_URL", "")
PROJECT_ID = os.environ.get("MONITORING_PROJECT_ID", "")
HMAC_SECRET = os.environ.get("MONITORING_HMAC_SECRET", "")
MASTER_ONLY = os.environ.get("MONITORING_HEARTBEAT_MASTER_ONLY", "1") == "1"


def _is_master_process() -> bool:
    """ADR-021: master-only check per Gunicorn/Uvicorn multi-worker."""
    if not MASTER_ONLY:
        return True
    try:
        return os.getpid() == os.getppid()
    except OSError:
        return True


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _send_heartbeat(service_id: str, max_retries: int) -> bool:
    if not HUB_URL or not PROJECT_ID or not HMAC_SECRET:
        return False

    payload = {
        "project_id": PROJECT_ID,
        "service_id": service_id,
        "timestamp": time.time(),
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, HMAC_SECRET)

    for attempt in range(max_retries):
        try:
            r = httpx.post(
                f"{HUB_URL}/api/v1/heartbeat",
                content=body,
                headers={"X-Signature": f"sha256={sig}", "Content-Type": "application/json"},
                timeout=3.0,
            )
            if r.status_code == 204:
                return True
            log.warning("heartbeat_rejected", extra={"status": r.status_code})
            return False
        except Exception as e:
            log.warning("heartbeat_failed", extra={"attempt": attempt, "error": str(e)})
            time.sleep(1 * (attempt + 1))
    return False


def _loop(service_id: str, interval: int, max_retries: int) -> None:
    while True:
        try:
            _send_heartbeat(service_id, max_retries)
        except Exception as e:
            log.error("heartbeat_loop_error", extra={"error": str(e)})
        time.sleep(interval)


class HeartbeatClient:
    _thread: Optional[threading.Thread] = None

    @classmethod
    def start_web(cls, service_id: Optional[str] = None) -> None:
        """Profilo web: heartbeat 60s, retry standard."""
        sid = service_id or os.environ.get("MONITORING_SERVICE_ID", "api")
        cls._start(sid, interval=60, max_retries=2)

    @classmethod
    def start_worker(cls, service_id: str) -> None:
        """Profilo worker: heartbeat 30s, retry aggressivo (5 tentativi)."""
        cls._start(service_id, interval=30, max_retries=5)

    @classmethod
    def _start(cls, service_id: str, interval: int, max_retries: int) -> None:
        if not _is_master_process():
            log.info("heartbeat_skipped_non_master_worker")
            return
        if cls._thread and cls._thread.is_alive():
            log.warning("heartbeat_already_started")
            return
        cls._thread = threading.Thread(
            target=_loop,
            args=(service_id, interval, max_retries),
            daemon=True,
            name=f"heartbeat-{service_id}",
        )
        cls._thread.start()
        log.info("heartbeat_started", extra={"service_id": service_id, "interval_s": interval})
