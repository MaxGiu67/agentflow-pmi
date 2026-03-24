---
name: AgentFlow PMI - stato progetto e decisioni live
description: Stato corrente del progetto AgentFlow, servizi esterni configurati, decisioni prese durante lo sviluppo
type: project
---

## Progetto AgentFlow PMI

### Deploy
- **Frontend**: https://frontend-production-2b11.up.railway.app
- **API**: https://api-production-15cd.up.railway.app
- **Railway Project ID**: 0f17983d-96bd-4868-8386-ce1dfbde02be
- **GitHub**: https://github.com/MaxGiu67/agentflow-pmi

### Servizi esterni configurati
- **Resend** (email): API key su Railway, dominio nexadata.it verificato, from: noreply@nexadata.it
- **FiscoAPI** (cassetto fiscale): chiave segreta su Railway, quota API Core esaurita — serve upgrade piano a pagamento
- **Salt Edge** (Open Banking): API keys su Railway, account Pending attivazione, API v6 (non v5)
- **A-Cube** (SDI fatturazione): non ancora attivato — candidato per ricezione fatture automatiche con codice destinatario

### Decisioni architetturali chiave
- **ADR-007**: Drop Odoo CE 18, sostituito con AccountingEngine interno
- **Bcrypt**: usato direttamente (`import bcrypt`) — passlib broken su Python 3.12
- **Datetime**: tutti i campi DB usano naive datetime (`.replace(tzinfo=None)`) per PostgreSQL TIMESTAMP WITHOUT TIME ZONE
- **SPID flow**: fallback a popup FiscoAPI portal quando API Core non disponibile

### Credenziali test
- admin@agentflow.it / Admin1Pass
- mgiurelli@taal.it / TestPass1

### Prossimi passi decisi
- Implementare ContoEconomicoAgent con Claude API per onboarding conversazionale
- Mapping ATECO → template conto economico
- Completare integrazione A-Cube per fatture automatiche (codice destinatario SDI)
- Attendere approvazione Salt Edge per banche italiane reali
- Attendere risposta FiscoAPI per piano a pagamento
