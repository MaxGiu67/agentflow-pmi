# Guida Setup Odoo 18 Online — CRM per AgentFlow PMI

> Riferimento: ADR-008 — Odoo 18 come CRM esterno (solo pipeline commerciale)

---

## 1. Accesso a Odoo 18 Online

1. Vai su https://nexadata.odoo.com
2. Login con le credenziali Nexa Data
3. Verifica di avere l'app **CRM** installata (menu Impostazioni > App)

Se il database non esiste ancora:
- Crea un trial su https://www.odoo.com/trial
- Scegli il piano **One App Free** (CRM gratis) oppure **Standard** (93 EUR/mese per 3 utenti)
- Database name: `nexadata`

---

## 2. Configurare la Pipeline

### 2.1 Stadi Pipeline

Vai su **CRM > Configurazione > Fasi** (oppure direttamente dalla Kanban, clicca "+ Fase"):

| Sequenza | Nome Fase | Probabilita |
|----------|-----------|-------------|
| 1 | Nuovo Lead | 10% |
| 2 | Qualificato | 30% |
| 3 | Proposta Inviata | 50% |
| 4 | Ordine Ricevuto | 80% |
| 5 | Confermato | 100% |

Per ogni fase, imposta la **probabilita** (campo "Probability" nella configurazione della fase).

### 2.2 Rimuovere fasi default

Odoo crea fasi default ("New", "Qualified", "Proposition", "Won"). Puoi rinominarle direttamente o cancellarle e creare quelle sopra.

---

## 3. Configurare i Campi Custom

Vai su **Impostazioni > Tecnico > Campi** (attiva Modalita Sviluppatore prima: Impostazioni > scroll in fondo > "Attiva modalita sviluppatore").

Crea i seguenti campi sul modello `crm.lead`:

| Campo Tecnico | Etichetta | Tipo | Note |
|---------------|-----------|------|------|
| `x_deal_type` | Tipo Deal | Selezione | Valori: T&M, fixed, spot, hardware |
| `x_daily_rate` | Tariffa Giornaliera | Float | EUR/giorno |
| `x_estimated_days` | Giorni Stimati | Float | Durata prevista |
| `x_technology` | Tecnologia | Testo | Stack tecnologico (Java, .NET, SAP...) |
| `x_order_type` | Tipo Ordine | Selezione | Valori: po, email, firma_word, portale |
| `x_order_reference` | Rif. Ordine Cliente | Testo | Numero PO / ODA |
| `x_order_date` | Data Ordine | Data | Data ricezione ordine |
| `x_order_notes` | Note Ordine | Testo Lungo | Dettagli processo cliente |

### Come creare un campo custom:

1. Apri un deal dalla Kanban CRM
2. Clicca icona **bug** in alto a destra (modalita sviluppatore)
3. Clicca **Modifica Vista**
4. Oppure: Impostazioni > Tecnico > Campi > Nuovo
   - **Modello**: `crm.lead`
   - **Nome campo**: `x_deal_type` (DEVE iniziare con `x_`)
   - **Tipo**: Selezione
   - **Etichetta**: "Tipo Deal"
   - Valori selezione: `[('T&M','T&M'),('fixed','Fixed'),('spot','Spot'),('hardware','Hardware')]`

---

## 4. Generare API Key

1. Vai su **Impostazioni** (icona ingranaggio)
2. Clicca il tuo nome utente in alto a destra > **Il mio profilo**
3. Tab **Sicurezza** (o "Account Security")
4. Sezione **API Keys** > **Nuovo API Key**
5. Descrizione: `AgentFlow PMI`
6. Copia la chiave generata (viene mostrata UNA SOLA VOLTA)
7. Salva la chiave nel file `.env` del progetto

```env
ODOO_API_KEY=la-chiave-copiata-qui
```

**IMPORTANTE**: L'API key sostituisce la password. NON usare la password dell'utente per le API.

---

## 5. Configurare .env

Aggiorna il file `.env` nella root del progetto:

```env
# Odoo 18 CRM (ADR-008)
ODOO_URL=https://nexadata.odoo.com
ODOO_DB=nexadata
ODOO_USER=mgiurelli@taal.it
ODOO_API_KEY=<la-api-key-generata>
ODOO_WEBHOOK_SECRET=<un-segreto-random-per-webhook>
```

Per generare un webhook secret:
```bash
openssl rand -hex 32
```

---

## 6. Verificare la Connessione

### Test da terminale

```bash
curl -s -X POST https://nexadata.odoo.com/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "service": "common",
      "method": "authenticate",
      "args": ["nexadata", "mgiurelli@taal.it", "<API_KEY>", {}]
    }
  }' | python3 -m json.tool
```

Dovrebbe restituire un `result` con l'UID numerico dell'utente (es. `2`).

### Test da AgentFlow

```bash
# Avvia il backend
cd "Gestione _Azienda"
python3 -m uvicorn api.main:app --reload

# Test endpoint pipeline
curl -s http://localhost:8000/api/v1/crm/pipeline/summary \
  -H "Authorization: Bearer <JWT_TOKEN>" | python3 -m json.tool
```

---

## 7. Configurare Webhook (Opzionale — Fase 2)

Per ricevere notifiche quando un deal viene confermato:

1. In Odoo: **Impostazioni > Tecnico > Azioni automatizzate**
2. Nuova azione:
   - **Modello**: Lead/Opportunita (crm.lead)
   - **Trigger**: Alla modifica del campo "Probabilita"
   - **Filtro**: Probabilita = 100 (deal vinto)
   - **Azione**: Esegui codice Python:

```python
import requests
url = "https://api.agentflow.nexadata.it/api/v1/webhook/deal-confirmed"
headers = {"X-Webhook-Secret": env["ODOO_WEBHOOK_SECRET"]}
data = {"deal_id": record.id, "name": record.name, "client": record.partner_id.name}
requests.post(url, json=data, headers=headers, timeout=10)
```

---

## 8. Utenti CRM

Per il piano Standard (3 utenti):

| Utente | Ruolo | Note |
|--------|-------|------|
| mgiurelli@taal.it | Admin + API | Genera API key |
| commerciale1@nexadata.it | Commerciale | Gestisce deal |
| commerciale2@nexadata.it | Commerciale | Gestisce deal |

Ogni utente viene assegnato ai propri deal. Il campo `user_id` in Odoo corrisponde al commerciale responsabile.

---

## 9. Checklist Pre-Go-Live

- [ ] Database Odoo 18 creato (`nexadata`)
- [ ] App CRM installata
- [ ] 5 fasi pipeline configurate (Nuovo Lead → Confermato)
- [ ] 8 campi custom `x_*` creati su `crm.lead`
- [ ] API Key generata e salvata in `.env`
- [ ] `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` nel `.env`
- [ ] Test connessione via curl OK
- [ ] Test endpoint `/crm/pipeline/summary` OK
- [ ] Utenti commerciali creati
- [ ] (Opzionale) Webhook azione automatizzata configurato

---

## Riferimenti

- ADR-008: `specs/technical/ADR-008-odoo-crm.md`
- Adapter: `api/adapters/odoo_crm.py`
- Module: `api/modules/crm/`
- Odoo JSON-RPC docs: https://www.odoo.com/documentation/18.0/developer/reference/external_api.html
