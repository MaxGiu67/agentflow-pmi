# Piano implementazione — Webhook A-Cube Open Banking + verifica firma

**Data:** 2026-04-22
**Sprint:** 48 US-OB-05
**Dipendenze:** Ticket A-Cube 05 (domande tecniche su HMAC — attesa risposta)

---

## Obiettivo

Creare un sistema di ricezione webhook A-Cube (`Connect`, `Reconnect`, `Payment`) che sia:

- **Sicuro**: valida che il messaggio arrivi davvero da A-Cube tramite firma digitale
- **Robusto**: gestisce retry, duplicati, errori di rete senza perdere eventi
- **Veloce**: risponde `200` entro 5 secondi, processing asincrono
- **Testabile**: firma verificabile in unit test senza chiamare A-Cube reale

---

## Architettura

```
┌─────────────────┐       HTTPS POST         ┌───────────────────────────┐
│  A-Cube         │  ─────────────────────→  │  AgentFlow API            │
│  (origine)      │  Header: X-Signature     │                           │
└─────────────────┘  Body: payload JSON      │  /webhooks/acube/{event}  │
                                             │         │                 │
                                             │         ▼                 │
                                             │  [1] Verify signature     │
                                             │         │ (HMAC-SHA256)   │
                                             │         ▼                 │
                                             │  [2] Parse payload        │
                                             │         │                 │
                                             │         ▼                 │
                                             │  [3] Idempotency check    │
                                             │         │ (event_id)      │
                                             │         ▼                 │
                                             │  [4] Enqueue background   │
                                             │         │                 │
                                             │         ▼                 │
                                             │  [5] Return 200 OK        │
                                             │                           │
                                             │  ───── async ─────        │
                                             │  Task Celery:             │
                                             │   - Update bank_connection│
                                             │   - Trigger sync_accounts │
                                             │   - Send notifications    │
                                             └───────────────────────────┘
```

---

## Componenti da costruire

### 1. Modulo `api/security/webhook_signature.py`

Utility generica per verifica firma HMAC, riutilizzabile (A-Cube + futuri webhook Brevo/Portal/ecc.).

```python
import hmac
import hashlib
from fastapi import Request, HTTPException

async def verify_hmac_signature(
    request: Request,
    *,
    header_name: str,
    shared_secret: str,
    algorithm: str = "sha256",
    body_hash: bool = False,
) -> bytes:
    """Verifica firma HMAC su una richiesta webhook.

    Ritorna il body raw (per parsing downstream).
    Raise HTTPException 401 se firma assente / invalida.
    """
    # leggi header firma
    received_sig = request.headers.get(header_name)
    if not received_sig:
        raise HTTPException(401, f"Missing signature header: {header_name}")

    # leggi body raw (PRIMA di parsing JSON — ordine byte critico)
    body = await request.body()

    # calcola firma attesa
    expected = hmac.new(
        shared_secret.encode("utf-8"),
        body,
        getattr(hashlib, algorithm),
    ).hexdigest()

    # compara constant-time (evita timing attack)
    if not hmac.compare_digest(expected, received_sig):
        raise HTTPException(401, "Invalid signature")

    return body
```

**Punti chiave:**
- `hmac.compare_digest` → confronto constant-time (evita side-channel attacks)
- Body raw letto **prima** del parsing JSON (ordine byte critico per firma)
- Algoritmo parametrizzato (da confermare via ticket: SHA256 / SHA512)
- Nome header parametrizzato (da confermare via ticket)

### 2. Tabella `webhook_events` per idempotency

```sql
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY,
    source VARCHAR(50) NOT NULL,      -- 'acube_ob', 'brevo', ecc.
    event_type VARCHAR(50) NOT NULL,  -- 'connect', 'reconnect', 'payment'
    external_id VARCHAR(255),          -- id evento A-Cube se presente
    fiscal_id VARCHAR(20),             -- P.IVA BR coinvolta
    payload JSONB NOT NULL,
    signature VARCHAR(512),            -- firma ricevuta (audit)
    received_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    processing_status VARCHAR(20) DEFAULT 'pending',  -- pending/processed/error
    processing_error TEXT,
    UNIQUE (source, event_type, external_id)
);
CREATE INDEX ix_webhook_events_status ON webhook_events (processing_status);
CREATE INDEX ix_webhook_events_received_at ON webhook_events (received_at);
```

**Strategia idempotency:**
- Se A-Cube espone un `event_id` nel payload → usa quello (ideale)
- Altrimenti → hash deterministico del body (`sha256(body)`) come fallback
- Constraint UNIQUE previene processing doppio in caso di retry A-Cube

### 3. Endpoint webhook (FastAPI)

File: `api/modules/banking/acube_ob_webhooks.py`

```python
from fastapi import APIRouter, Request, BackgroundTasks, Depends

router = APIRouter(prefix="/webhooks/acube", tags=["webhooks-acube"])

@router.post("/connect", status_code=200)
async def webhook_connect(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    body = await _verify_and_load(request)
    event = await _persist_event(db, "connect", body)
    if event.is_duplicate:
        return {"status": "duplicate_ignored"}
    background_tasks.add_task(process_connect_event, event.id)
    return {"status": "accepted", "event_id": str(event.id)}

# stesso pattern per /reconnect e /payment
```

**Pattern "fast return":**
- Verifica + persist in < 500ms
- Task in background (non blocca la risposta)
- A-Cube riceve `200 OK` velocemente → non fa retry
- Il processing reale (sync accounts, notifiche email) avviene dopo

### 4. Background processors

File: `api/modules/banking/acube_ob_processors.py`

```python
async def process_connect_event(event_id: UUID):
    """Processa un evento Connect dopo conferma 200 al chiamante."""
    # 1. Carica event da DB
    # 2. Se success → update bank_connection.status='active'
    # 3. Trigger sync_accounts per ogni updatedAccounts
    # 4. Aggiorna event.processed_at, event.processing_status='processed'

async def process_reconnect_event(event_id: UUID):
    """Salva reconnect_url + notice_level + trigger email notifica."""

async def process_payment_event(event_id: UUID):
    """Update status payment + notifica user."""
```

### 5. Modalità "firma opzionale" per sandbox

Env var `ACUBE_OB_WEBHOOK_VERIFY_SIGNATURE` (default `true`):

```python
if settings.acube_ob_webhook_verify_signature:
    await verify_hmac_signature(request, header_name="X-Acube-Signature", ...)
else:
    logger.warning("Webhook signature verification DISABLED — sandbox mode")
    body = await request.body()
```

**Uso:**
- **Produzione**: sempre `true`
- **Sandbox iniziale**: `false` per test con webhook.site / cURL locale
- **Sandbox finale**: `true` quando abbiamo la chiave vera da A-Cube

### 6. Test strategia

**Test unitari firma** (`tests/test_webhook_signature.py`):
- Firma valida → verifica passa
- Firma invalida → 401
- Header assente → 401
- Body modificato → 401 (rileva manomissione)
- Algoritmo errato → 401
- Constant-time comparison (non testabile ma documentato)

**Test integrazione webhook** (`tests/test_acube_ob_webhooks.py`):
- POST /webhooks/acube/connect con payload + firma corretta → 200 + event persisted
- POST stesso payload 2 volte → secondo ritorna `duplicate_ignored`
- POST senza firma in modalità strict → 401
- POST con firma errata → 401
- Side effect: bank_connection.status diventa `active` dopo processing
- Side effect: reconnect invia email notifica via mock Brevo

---

## Sequenza implementazione (senza bloccare su A-Cube)

### Fase 1 — Scaffolding (possibile ORA, no dipendenze)

1. Tabella `webhook_events` + modello SQLAlchemy
2. Modulo `security/webhook_signature.py` con firma HMAC generica
3. Endpoint `/webhooks/acube/{connect,reconnect,payment}` con signature verification **OPZIONALE** (env flag)
4. Background processors che agganciano `bank_connections`
5. Test unitari firma (indipendenti dal nome header A-Cube)
6. Test integrazione in **modalità insecure** (`verify_signature=false`)

**Risultato:** webhook funzionanti in sandbox, accettano payload non firmati.

### Fase 2 — Hardening (dopo risposta Ticket 05)

Quando A-Cube risponde, sappiamo:
- Header esatto (es. `X-Acube-Signature`)
- Algoritmo (es. SHA256)
- Formato firma (es. hex lowercase)
- Payload firmato (body raw o body+timestamp)
- Chiave segreta

**Modifiche minime:**
1. Set env var `ACUBE_OB_WEBHOOK_SECRET` con la chiave vera
2. Set `ACUBE_OB_WEBHOOK_VERIFY_SIGNATURE=true`
3. Adatta costanti `SIGNATURE_HEADER_NAME`, `SIGNATURE_ALGORITHM` se diverse dai default
4. Aggiungi test con firma calcolata (fixture con chiave + payload + expected signature)

**Stima hardening:** 2-4 ore, 1 deploy.

### Fase 3 — Produzione

1. Configurare webhook nella dashboard A-Cube **produzione**
2. URL: `https://agentflow.up.railway.app/api/v1/webhooks/acube/connect` (idem reconnect, payment)
3. Authentication type: HMAC (o quello confermato)
4. Chiave segreta: generata e condivisa con noi
5. IP whitelist firewall Railway per IP A-Cube (se disponibile — da ticket 05)

---

## Security checklist

| ✓ | Item |
|---|---|
| ☐ | HMAC con `hmac.compare_digest` (constant-time) |
| ☐ | Body letto **raw** prima di parsing JSON (ordine byte preservato) |
| ☐ | Secret in env var, mai in repo |
| ☐ | Secret ruotato ogni 6 mesi (procedura documentata) |
| ☐ | Rate limit su endpoint webhook (1000 req/min per IP) |
| ☐ | Payload size limit (max 1MB) |
| ☐ | Timeout totale 5s (richiesta A-Cube si chiude rapidamente) |
| ☐ | Log firma ricevuta (audit) ma mai secret in chiaro |
| ☐ | Idempotency via UNIQUE constraint su `(source, event_type, external_id)` |
| ☐ | Se A-Cube lo fornisce: whitelist IP su firewall |
| ☐ | TLS 1.2+ enforced (Railway già compliant) |
| ☐ | HTTPS-only (no HTTP) |
| ☐ | Replay protection: rifiuta eventi con `timestamp` > 5 min dal now |

---

## Protezione dai retry A-Cube

A-Cube probabilmente fa retry automatico se risposta ≠ 2xx (da confermare via Ticket 05).

**Strategia:**
- Rispondiamo `200 OK` anche su eventi duplicati (A-Cube smette di riprovare)
- Idempotency via DB UNIQUE → no doppio processing
- Se processing background fallisce, **non rispondiamo con errore** al chiamante (sarebbe già troppo tardi) — lo gestiamo con retry interno Celery

```python
try:
    await _verify_and_load(request)
    event = await _persist_event(...)
    background_tasks.add_task(...)
    return {"status": "accepted"}
except InvalidSignature:
    return JSONResponse(status_code=401, content={"error": "invalid_signature"})
except DuplicateEvent:
    return {"status": "duplicate_ignored"}  # 200 OK deliberato
except Exception as e:
    logger.exception("Webhook processing error")
    return {"status": "error"}  # 200 OK — non vogliamo retry storm
```

---

## Domande aperte (dal Ticket 05)

Punti da chiarire con A-Cube prima della Fase 2:

1. ☐ Algoritmo firma (HMAC-SHA256 presumibile, confermare)
2. ☐ Nome header contenente la firma
3. ☐ Formato firma (hex lowercase? base64? prefisso tipo `sha256=...`?)
4. ☐ Payload firmato (body raw / body+timestamp / body+url)
5. ☐ Come otteniamo la chiave segreta (generata da noi? da A-Cube? dashboard?)
6. ☐ Rotazione chiave: procedura consigliata
7. ☐ Retry policy (tentativi, backoff, disabilitazione automatica)
8. ☐ IP allow-list A-Cube per whitelist firewall
9. ☐ Esiste un `event_id` nel payload per idempotency nativa?
10. ☐ Test harness A-Cube per triggerare webhook manualmente dalla dashboard?

---

## File da creare

| # | File | Scope |
|---|------|-------|
| 1 | `api/db/models/webhooks.py` (o aggiunta a `other.py`) | Modello `WebhookEvent` |
| 2 | `api/security/webhook_signature.py` | Utility HMAC verify (riusabile) |
| 3 | `api/modules/banking/acube_ob_webhooks.py` | 3 endpoint: connect / reconnect / payment |
| 4 | `api/modules/banking/acube_ob_processors.py` | Business logic background |
| 5 | `tests/test_webhook_signature.py` | Test firma HMAC (10+ casi) |
| 6 | `tests/test_acube_ob_webhooks.py` | Test integrazione webhook (8+ casi) |
| 7 | `api/config.py` | Aggiunge `acube_ob_webhook_verify_signature` + `acube_ob_webhook_secret` |
| 8 | `api/main.py` | Router register + ALTER TABLE per `webhook_events` |

**Totale stimato:** ~700 righe di codice + test, 1-2 giornate di lavoro.

---

## Metriche di successo

1. **Latency p95** risposta webhook < 500ms (A-Cube non fa retry inutili)
2. **Zero duplicati processati** (idempotency funziona)
3. **100% eventi auditabili** (tabella `webhook_events` contiene tutto storico)
4. **0 leak** di chiave segreta in log, DB errore, response body
5. **Test coverage > 90%** su moduli signature + webhooks
6. **Security review** passata (checklist sopra completa)

---

## Rollout plan

1. **Dev sandbox** — webhook receiver attivo, firma opzionale, test con webhook.site
2. **Dev sandbox hardened** — firma attiva (dopo risposta Ticket 05), test con cURL firmato
3. **Staging** — webhook registrato su A-Cube sandbox dashboard, test con flow reale Connect
4. **Produzione canary** — abilitato per 1 cliente pilota, monitoraggio 48h
5. **Produzione full** — rollout completo

---

## Disaster recovery

Se webhook A-Cube smette di funzionare (bug, disabilitazione, outage):

1. **Polling fallback** — Celery beat daily `GET /business-registry/*/accounts` + `GET /transactions`
2. **Recovery manuale** — endpoint admin `/api/v1/admin/webhook-replay/{event_id}` per ri-processare eventi
3. **Alert** — notifica Slack se `processed_at` resta null per > 1h su eventi nuovi
