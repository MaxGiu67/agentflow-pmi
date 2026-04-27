# State Snapshot Endpoints — infrastruttura per agenti AI

## Scopo

Endpoint REST aggregati che ritornano lo **stato completo di un dominio**
in 1 sola chiamata HTTP. Pensati per essere il "tool primario" che gli
agenti AI (Sales/Controller/Analytics) leggono per "vedere tutto".

## Endpoint disponibili

| URL | Cosa ritorna | Usato da |
|---|---|---|
| `GET /api/v1/state/banking` | Saldi, mov 30/60/90gg, top counterparts, anomalie, runway | Controller, Analytics |
| `GET /api/v1/state/invoicing` | Fatture attive/passive YTD, IVA Q, scadenze 30gg, top clienti/fornitori | Controller |
| `GET /api/v1/state/sales` | Pipeline, deal stagnanti, win rate, attività programmate | Sales, Analytics |
| `GET /api/v1/state/all` | Tutti e 3 in parallelo (asyncio.gather) + all_flags | Chatbot Orchestrator |

## Caratteristiche

- **100% async** — `async def` + AsyncSession SQLAlchemy
- **Tenant-isolated** — sempre filtra per `user.tenant_id`
- **Read-only** — nessuna scrittura
- **Aggregato** — denormalizza in dict piatti, no N+1 da parte dell'agente
- **Self-contained** — ogni snapshot ha la sua "verità" senza altre chiamate

## Esempio chiamata `/banking`

```json
{
  "tenant_piva": "12136821001",
  "snapshot_at": "2026-04-27T11:30:00Z",
  "accounts_total": 2,
  "accounts": [
    {
      "iban": "IT90B0306914898100000004144",
      "bank_name": "Intesa Sanpaolo",
      "balance": 440.74,
      "transactions_count": 25,
      "consent_expires_at": "2026-07-25T18:44:42Z"
    }
  ],
  "total_balance": 912.42,
  "tx_30d_in": 1000.00,
  "tx_30d_out": -2538.40,
  "tx_30d_net": -1538.40,
  "tx_90d_count": 35,
  "top_categories_30d": [
    {"category": "loan_payment", "count": 1, "total_amount": 1000.0},
    {"category": "fee", "count": 12, "total_amount": 153.40}
  ],
  "top_counterparts_in_30d": [
    {"name": "QUBIKA S.R.L.", "direction": "in", "total_amount": 1000.0, "transactions_count": 1}
  ],
  "runway_months_estimate": 0.5,
  "avg_monthly_burn": 1820.0,
  "anomalies": [],
  "flags": ["low_runway_under_2_months"]
}
```

## Flags — segnali per agenti

I `flags[]` sono stringhe machine-readable che gli agenti possono
controllare per attivare comportamenti specifici:

### Banking flags
- `no_bank_accounts_connected`
- `negative_total_balance`
- `low_runway_under_2_months`
- `burn_exceeds_revenue_3m`
- `consent_expiring_soon_{IBAN}`
- `stale_sync_{IBAN}` (>7gg dall'ultimo sync)

### Invoicing flags
- `sdi_rejected_{N}_invoices`
- `sdi_pending_{N}_invoices`
- `passive_uncategorized_{N}`
- `overdue_active_{X}_eur`
- `high_iva_debit_q`

### Sales flags
- `no_deals`
- `majority_deals_stagnant`
- `win_rate_below_20pct`
- `activities_overdue_{N}`
- `no_new_deals_this_month`

## Performance

- Query DB ottimizzate per single round-trip per dominio
- `/state/all` parallelizza i 3 sub-snapshot con `asyncio.gather`
- Latenza tipica:
  - `/state/banking` solo: ~80-150ms (50-200 tx)
  - `/state/all` parallelo: ~150-300ms (3 snapshot insieme)

## Prossimi step (Sprint 51+)

1. **Wire agenti esistenti** — Controller agent legge `/state/all` come
   primo tool quando utente chiede "come stiamo?"
2. **Event bus** (`tenant_events`) — generare eventi su `flags` rilevanti
3. **Agent state memory** — tabella `agent_state` per memoria cross-session
4. **Cron daily** — chiamata `/state/all` schedulata che genera proactive alerts
