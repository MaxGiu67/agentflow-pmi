#!/usr/bin/env python3
"""Smoke test reale contro A-Cube Open Banking sandbox.

Uso:
    # 1. Settare credenziali in .env:
    #    ACUBE_OB_ENV=sandbox
    #    ACUBE_OB_LOGIN_EMAIL=tua@email
    #    ACUBE_OB_LOGIN_PASSWORD=tuaPwd
    # 2. Lanciare:
    #    python3 scripts/smoke_acube_ob.py

Non crea Business Registry (fee charged).
Solo operazioni di lettura + login.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Aggiungi root repo al path per importare api.*
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Carica .env manualmente (senza dipendere da dotenv se non installato)
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            import os
            os.environ.setdefault(k.strip(), v)

from api.adapters.acube_ob import (  # noqa: E402
    ACubeAPIError,
    ACubeAuthError,
    ACubeOpenBankingClient,
)


# ── Colori console ─────────────────────────────────────────
C_OK = "\033[92m"
C_ERR = "\033[91m"
C_INFO = "\033[94m"
C_WARN = "\033[93m"
C_BOLD = "\033[1m"
C_END = "\033[0m"


def banner(text: str) -> None:
    print(f"\n{C_BOLD}{C_INFO}━━━ {text} ━━━{C_END}")


def ok(msg: str) -> None:
    print(f"{C_OK}✔{C_END}  {msg}")


def err(msg: str) -> None:
    print(f"{C_ERR}✖{C_END}  {msg}")


def info(msg: str) -> None:
    print(f"{C_INFO}ℹ{C_END}  {msg}")


def warn(msg: str) -> None:
    print(f"{C_WARN}⚠{C_END}  {msg}")


def json_preview(data, n: int = 3) -> str:
    if isinstance(data, list):
        return json.dumps(data[:n], indent=2, ensure_ascii=False)
    return json.dumps(data, indent=2, ensure_ascii=False)


# ── Smoke test ─────────────────────────────────────────────

async def main() -> int:
    client = ACubeOpenBankingClient()

    banner("Configurazione")
    info(f"Env: {client.env}")
    info(f"Login URL: {client.login_url}")
    info(f"Base URL: {client.base_url}")
    info(f"Email: {client.email or '(vuoto)'}")
    info(f"Password: {'*' * len(client.password) if client.password else '(vuoto)'}")

    if not client.enabled:
        err("Client disabilitato — manca ACUBE_OB_LOGIN_EMAIL o ACUBE_OB_LOGIN_PASSWORD in .env")
        info("Aggiungi al file .env:")
        print("""
    ACUBE_OB_ENV=sandbox
    ACUBE_OB_LOGIN_EMAIL=tua@email
    ACUBE_OB_LOGIN_PASSWORD=tuaPassword
""")
        return 1

    # ── Test 1: Login ───────────────────────────────────────
    banner("Test 1 — POST /login (ottenimento JWT)")
    try:
        token = await client._login()
        ok(f"Login riuscito — JWT lungo {len(token)} caratteri")
        info(f"Token prefix: {token[:40]}…")
    except ACubeAuthError as e:
        err(f"Login fallito: {e}")
        info("Verifica email/password su https://dashboard.acubeapi.com")
        return 1

    # ── Test 2: Caching JWT ─────────────────────────────────
    banner("Test 2 — Cache JWT (nessun re-login)")
    import time
    t0 = time.time()
    tok1 = await client._get_token()
    t1 = time.time()
    tok2 = await client._get_token()
    t2 = time.time()
    if tok1 == tok2:
        ok(f"Cache OK — token identico, 1° chiamata {(t1-t0)*1000:.0f}ms, 2° chiamata {(t2-t1)*1000:.0f}ms")
    else:
        err("Cache non funziona — token diverso tra chiamate ravvicinate")
        return 1

    # ── Test 3: GET /business-registry (no fee) ─────────────
    banner("Test 3 — GET /business-registry (lista BR esistenti)")
    try:
        brs = await client.list_business_registries()
        ok(f"Lista recuperata — {len(brs)} Business Registry")
        if brs:
            info("Primi 3 BR:")
            print(json_preview(brs, 3))
        else:
            info("Lista vuota — atteso per account appena creato")
    except ACubeAPIError as e:
        err(f"API error HTTP {e.status_code}: {e.body[:200]}")
        return 1

    # ── Test 4: GET /categories (tassonomia) ────────────────
    banner("Test 4 — GET /categories (tassonomia transazioni)")
    try:
        cats = await client.list_categories()
        ok(f"Categorie recuperate — {len(cats)} totali")
        if cats:
            info("Prime 5 categorie:")
            print(json_preview(cats, 5))
    except ACubeAPIError as e:
        err(f"API error HTTP {e.status_code}: {e.body[:200]}")

    # ── Test 5: GET dettaglio BR (solo se ne esistono) ──────
    if brs:
        banner("Test 5 — GET /business-registry/{fiscalId} (dettaglio)")
        first_fid = brs[0].get("fiscalId")
        if first_fid:
            try:
                detail = await client.get_business_registry(first_fid)
                ok(f"Dettaglio BR {first_fid} recuperato")
                info("Campi:")
                print(json_preview(detail))
            except ACubeAPIError as e:
                err(f"Errore dettaglio BR: HTTP {e.status_code}")

    # ── Report finale ───────────────────────────────────────
    banner("Report finale")
    ok("Smoke test completato — il client ACubeOpenBankingClient funziona contro la sandbox")
    info("Prossimi step consigliati:")
    print("  1. Creare un Business Registry test (ATTENZIONE: fee charged, anche se sandbox)")
    print("     → valutare se preferiamo prima chiarire via ticket")
    print("  2. Avviare un flusso Connect PSD2 (simulazione con country='XF')")
    print("  3. Procedere con Sprint 48 US-OB-03 (modelli DB)")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrotto dall'utente.")
        exit_code = 130
    except Exception as e:  # noqa: BLE001
        print(f"\n{C_ERR}Errore imprevisto:{C_END} {e}")
        import traceback
        traceback.print_exc()
        exit_code = 2
    sys.exit(exit_code)
