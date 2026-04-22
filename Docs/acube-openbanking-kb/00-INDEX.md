# A-Cube Open Banking — Knowledge Base interna

**Fonte:** `docs.acubeapi.com` (consultata il 2026-04-19)
**Scopo:** Base di conoscenza completa estratta dalla documentazione pubblica A-Cube, pronta per lo sviluppo Pivot 11 "Finance Cockpit" di AgentFlow.

---

## Indice file

| # | File | Contenuto |
|---|------|-----------|
| 00 | [INDEX](./00-INDEX.md) | Questo indice + convenzioni |
| 01 | [Overview + Ambienti](./01-overview-ambienti.md) | Concetto, attori, sandbox/prod, ultimo update docs |
| 02 | [Autenticazione](./02-authentication.md) | POST /login, JWT, Bearer, durata token |
| 03 | [Connection Process PSD2](./03-connection-process.md) | Flusso 9 step consenso end-user |
| 04 | [Webhooks](./04-webhooks.md) | Connect / Reconnect / Payment con payload completi |
| 05 | [Accounts + Transactions](./05-accounts-transactions.md) | Lettura conti e movimenti |
| 06 | [Payments (Outbound + Request to Pay)](./06-payments.md) | Bonifici uscita + richieste pagamento |
| 07 | [API Reference completa](./07-api-reference.md) | Tutti gli endpoint con path/metodo/parametri |
| 08 | [Schemi dati](./08-schemas.md) | Account, Transaction, BusinessRegistry, ecc. |
| 09 | [FAQ + Gotchas](./09-faq-gotchas.md) | Domande frequenti + tranelli pratici |
| 10 | [Cassetto Fiscale](./10-cassetto-fiscale.md) | Altro servizio A-Cube (scarico massivo fatture) |
| 11 | [Servizi Italia](./11-italy-services.md) | Catalogo completo prodotti A-Cube per IT |
| 12 | [Supporto](./12-support.md) | Canali assistenza + ticketing |
| 99 | [Open Questions](./99-open-questions.md) | Domande non coperte dai docs (da chiedere ad A-Cube) |

---

## Convenzioni usate in questa KB

- **Codice/path** in `monospace`
- **Curl** completi con tutti gli header
- **Schemi JSON** verbatim dalla documentazione
- **⚠️** marker per gotchas noti
- **❓** marker per informazioni non presenti nei docs (da verificare)

---

## Riferimenti esterni

- Documentazione pubblica: https://docs.acubeapi.com/documentation/open-banking/
- OpenAPI spec scaricabile: https://docs.acubeapi.com/openapi/open-banking-api.json
- Portale A-Cube: https://dashboard.acubeapi.com
- Sito commerciale: https://acubeapi.com
- Blog novità: https://blog.acubeapi.com
- Support email (fino al 7/4): `support@a-cube.io` (deprecato — ora ticketing)
- PEC: `acubesrl@legalmail.it`

## Contesto contrattuale

Contratto NexaData firmato 10/04/2026 (rif. `project_acube_contract`). Copre:
- **Open Banking AISP** — setup €900 una tantum + €1.200/anno canone (fascia 1-50 P.IVA)
- **Scarico Massivo Fatture Cassetto Fiscale** — €600/anno (5 clienti + 5.000 fatture)
