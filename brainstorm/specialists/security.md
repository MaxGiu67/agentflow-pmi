# Analisi Sicurezza & Privacy — ContaBot

**Data:** 2026-03-22
**Classificazione:** D7=2 (dati sensibili — fatture, dati fiscali, credenziali email)

---

## Threat Model Light

### Asset da Proteggere

| Asset | Sensibilità | Dove risiede |
|-------|:-----------:|-------------|
| Fatture (PDF/XML) | ALTA | S3 encrypted |
| Dati strutturati fatture (importi, CF, P.IVA) | ALTA | PostgreSQL |
| Token OAuth Gmail | CRITICA | Secrets Manager |
| Credenziali utente | ALTA | DB (bcrypt hash) |
| Modello learning per utente | MEDIA | PostgreSQL/S3 |
| Log e audit trail | MEDIA | CloudWatch/DB |

### Threat Actors

1. **Attaccante esterno** — Accesso non autorizzato a dati finanziari, phishing
2. **Insider malevolo** — Sviluppatore/operatore con accesso ai sistemi
3. **Supply chain** — Vulnerabilità in dipendenze (librerie Python, npm)
4. **Competitor** — Scraping, reverse engineering del learning engine

### Vettori di Attacco Principali

| # | Vettore | Probabilità | Impatto | Mitigazione |
|---|---------|:-----------:|:-------:|-------------|
| 1 | **Compromissione OAuth token Gmail** | Media | Critico | Encryption at-rest, rotation automatica, scope minimo |
| 2 | **SQL injection su API** | Bassa | Critico | ORM (SQLAlchemy), input validation, parameterized queries |
| 3 | **XSS su frontend** | Media | Alto | React sanitization, CSP headers, input sanitization |
| 4 | **IDOR su fatture** (accesso fatture di altri utenti) | Media | Critico | Middleware authorization su ogni endpoint, test automatici |
| 5 | **Brute force login** | Media | Medio | Rate limiting, bcrypt con salt, MFA (P1) |
| 6 | **Data leak via OCR service** | Bassa | Alto | Google Cloud Vision con data residency EU, DPA firmato |
| 7 | **Man-in-the-middle** | Bassa | Alto | TLS 1.2+ everywhere, HSTS, certificate pinning |
| 8 | **Backup non crittografati** | Bassa | Critico | Encryption AES-256 su backup S3, access logging |

---

## Checklist GDPR / Privacy

### Dati Personali Trattati

| Dato | Categoria | Base giuridica |
|------|-----------|---------------|
| Nome, email utente | Identificativo | Art. 6(1)(b) — esecuzione contratto |
| Codice Fiscale, P.IVA | Fiscale | Art. 6(1)(b) + Art. 6(1)(c) — obbligo legale |
| Contenuto fatture | Finanziario | Art. 6(1)(b) — esecuzione contratto |
| Indirizzo (in fatture) | Identificativo | Art. 6(1)(b) — necessario per servizio |
| Gmail OAuth token | Tecnico | Art. 6(1)(a) — consenso esplicito |
| Pattern categorizzazione | Profilazione | Art. 6(1)(a) — consenso + legittimo interesse |

### Requisiti Privacy MVP

- [ ] **Informativa privacy** completa (art. 13/14 GDPR)
- [ ] **Consenso OAuth** esplicito con spiegazione scope
- [ ] **Cookie policy** (solo tecnici per MVP, no analytics tracking)
- [ ] **Data retention policy**: fatture 10 anni (obbligo D.P.R. 633/1972), account data 2 anni post-cancellazione
- [ ] **Diritto di accesso**: export JSON di tutti i dati utente
- [ ] **Diritto di portabilità**: export in formato standard (CSV/JSON)
- [ ] **Diritto di cancellazione**: cancellazione account con retention obbligatoria fatture
- [ ] **DPA con Google** (Gmail API, Cloud Vision) — verificare copertura EU
- [ ] **DPA con AWS** — già coperto da AWS Data Processing Addendum
- [ ] **DPIA** (Data Protection Impact Assessment) — obbligatoria prima del lancio (trattamento dati su larga scala)
- [ ] **Registro dei trattamenti** (art. 30 GDPR)

---

## Controlli di Sicurezza MVP

### P0 — Prima del Beta Test

| Controllo | Implementazione | Effort |
|-----------|----------------|--------|
| **Autenticazione** | OAuth2 (Google) + JWT con expiry 1h | S |
| **Autorizzazione** | RBAC basilare (owner, viewer) + row-level security su fatture | M |
| **TLS everywhere** | HTTPS su tutti gli endpoint, HSTS header | S |
| **Secrets management** | AWS Secrets Manager per OAuth tokens, DB credentials | S |
| **Input validation** | Pydantic models su FastAPI, sanitizzazione input | S |
| **OWASP Top 10** | Hardening base: CSP, X-Frame-Options, rate limiting | M |
| **Privacy policy** | Documento legale + consent flow in-app | S (legal) |
| **Audit log minimo** | Log login, accesso fatture, modifiche (90 giorni) | M |

### P1 — Prima del Lancio Pubblico

| Controllo | Implementazione | Effort |
|-----------|----------------|--------|
| **MFA** | TOTP (Google Authenticator) obbligatorio | M |
| **Penetration test** | Audit esterno su API e frontend | L (€5-10k) |
| **DPA firmati** | Con tutti i sub-processor (Google, AWS) | S (legal) |
| **DPIA completata** | Assessment formale con DPO | M (legal) |
| **Incident response plan** | Procedura notifica data breach (72h GDPR) | S |
| **Backup crittografati** | AES-256 su S3, test restore mensile | S |

### P2 — Entro 6 Mesi dal Lancio

| Controllo | Implementazione | Effort |
|-----------|----------------|--------|
| **ISO 27001 assessment** | Gap analysis per certificazione futura | L |
| **SOC 2 Type I** | Se target B2B (commercialisti) lo richiede | L |
| **Encryption client-side** | Opzionale per utenti con requisiti elevati | L |
| **WebAuthn/Passkeys** | Login passwordless | M |
| **Vulnerability scanning** | Automatico su CI/CD (Snyk, Trivy) | S |

---

## Compliance Specifica Italiana

### Conservazione Digitale Fatture
- **Obbligo:** Le fatture elettroniche devono essere conservate per 10 anni (art. 39 D.P.R. 633/1972)
- **Requisiti:** Integrità, leggibilità, accessibilità nel tempo
- **Opzione MVP:** Conservazione sostitutiva tramite provider certificato (Aruba, InfoCert) oppure hash di integrità + timestamp trusted
- **Raccomandazione:** Per MVP, hash SHA-256 su ogni fattura + timestamp. Per produzione, partnership con conservatore accreditato AgID

### Trattamento Dati Fiscali
- Non servono certificazioni specifiche per trattare dati fiscali altrui
- MA: se il servizio si configura come "intermediario telematico" verso AdE, servono autorizzazioni specifiche
- **Raccomandazione MVP:** NON essere intermediario. L'utente scarica i dati e li porta al commercialista

### PEC (Posta Elettronica Certificata)
- Non necessaria per MVP
- Sarà necessaria se ContaBot invierà comunicazioni ufficiali per conto dell'utente

---

## Costi Stimati Security

| Fase | Costo | Timeline |
|------|-------|----------|
| P0 (Beta) | €3-5k (engineering) + €1-2k (legal) | 2-3 settimane |
| P1 (Lancio) | €5-10k (pentest) + €2-3k (legal/DPIA) | 3-4 settimane |
| P2 (6 mesi) | €10-15k (ISO assessment + tooling) | 4-6 settimane |
| **Totale anno 1** | **€20-35k** | |

---

## Raccomandazioni Prioritizzate

1. **SUBITO:** OAuth tokens encrypted at-rest + RBAC + TLS — è il minimo per gestire dati finanziari
2. **PRIMA DEL BETA:** Privacy policy + audit log + input validation — senza questi non puoi coinvolgere utenti reali
3. **PRIMA DEL LANCIO:** DPIA + pentest + MFA — obbligatori per dati sensibili
4. **ATTENZIONE:** Non diventare intermediario telematico AdE — cambia completamente i requisiti normativi

---
_Security & Privacy completata — 2026-03-22_
