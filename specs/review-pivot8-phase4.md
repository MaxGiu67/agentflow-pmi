# Code Review — Pivot 8: Phase 4 (Tech Spec + Schema + Wireframes + Stories)

**Reviewer:** Claude (Engineering Code Review)
**Data:** 2026-04-04
**Scope:** specs/04-tech-spec-pivot8.md, specs/database/schema-pivot8.md, specs/ux/wireframes-pivot8.md, specs/03-user-stories-pivot8-social.md

---

## Rating Summary

| Dimensione | Voto | Commento |
|------------|------|----------|
| **Security** | 8/10 | RBAC design solido, audit trail immutabile, ma mancano dettagli su rate limiting per endpoint sensibili e sanitizzazione JSONB |
| **Performance** | 7/10 | Indici strategici presenti, ma rischio N+1 su compensation calculation e dashboard widget; manca strategia di caching Redis |
| **Correctness** | 8/10 | Schema DB coerente con stories, buoni edge case negli AC, alcune inconsistenze naming da risolvere |
| **Maintainability** | 9/10 | Ottima struttura modulare, ADR ben documentato, business rules enumerate, dependency graph chiaro |

**Overall: 8/10** — Spec di alta qualità, pronta per sprint planning con le correzioni segnalate sotto.

---

## CRITICAL Issues (da risolvere PRIMA dello sprint planning)

### C1: Inconsistenza naming `is_prefunnel` vs `stage_type`
**File:** stories US-136 (AC-136.1) vs tech-spec (riga 172) vs schema (riga 493-494)
**Problema:** La story US-136.1 usa `is_prefunnel = true` come campo booleano, mentre la tech spec e il DDL definiscono `stage_type VARCHAR(50)` con enum `('pre_funnel', 'pipeline')`. Sono due approcci diversi.
**Fix:** Allineare la story US-136.1 per usare `stage_type = 'pre_funnel'` (l'approccio enum è migliore perché estensibile — domani potresti aggiungere "post_pipeline" o "archived").

### C2: Conteggio stories inconsistente
**File:** stories summary table (riga 629) dice "20 User Stories, 120 SP" ma l'overview (riga 6) dice "5 Epic, 21 story" e il _status.md elenca US-100→US-120 = 21 stories.
**Fix:** Correggere la summary table a "21 User Stories".

### C3: `crm_contacts.origin_id` — constraint conflitto con migration
**File:** schema-pivot8.md (righe 445-446)
**Problema:** Il DDL aggiunge un CHECK constraint `origin_id IS NOT NULL OR status IN ('archived', 'deleted')`, ma la migration (righe 458-484) lascia origin_id NULL per contatti con source=NULL. Questo genera conflitto: contatti attivi senza origin crasherebbero dopo la migration.
**Fix:** La migration deve assegnare un'origine di default (es. "unknown" o "da_classificare") ai contatti con source NULL, oppure il CHECK constraint va applicato solo DOPO il backfill completo (migration in 2 step: 1. add column nullable, 2. backfill, 3. add constraint).

### C4: `crm_product_categories` referenziata prima della creazione
**File:** schema-pivot8.md — Tabella `crm_products` (riga 216) ha FK su `crm_product_categories`, ma `crm_product_categories` è definita DOPO (riga 249).
**Fix:** Riordinare DDL: creare `crm_product_categories` PRIMA di `crm_products`. Aggiungere nota nell'ordine di migrazione.

---

## HIGH Issues

### H1: JSONB `dashboard_layout` — nessuna validazione schema
**File:** tech-spec (righe 379-411), schema (righe 299-317)
**Problema:** Il campo `dashboard_layout JSONB NOT NULL` accetta qualsiasi JSON. Nessun JSON Schema validation è specificato. Un utente potrebbe salvare JSON malformato che crasha il frontend.
**Raccomandazione:** Aggiungere validazione Pydantic del JSON schema lato API (es. definire `DashboardLayoutSchema` con widget_id, type, title, period required). Opzionalmente, aggiungere CHECK constraint PostgreSQL con `jsonb_typeof(dashboard_layout) = 'object'`.

### H2: JSONB `base_config` e `conditions` su compensation — injection risk
**File:** tech-spec (righe 443-474), schema (righe 326-354)
**Problema:** `base_config` e `conditions` sono JSONB con strutture complesse (tiers, formulas). Se `calculation_method = 'formula'`, il campo potrebbe contenere espressioni arbitrarie. Non è specificata nessuna sanitizzazione o sandboxing.
**Raccomandazione:** Per MVP, rimuovere `calculation_method = 'formula'` (troppo rischioso senza sandbox). Limitare a `percent_revenue`, `fixed_amount`, `tiered`. Se serve formula, usare libreria safe-eval con whitelist di funzioni.

### H3: Seed data con `'tenant-123'` hardcoded
**File:** tech-spec (righe 126-132, 156-164, 193-198, 220-242), schema (righe 520-599)
**Problema:** Gli INSERT di seed data usano `'tenant-123'` come placeholder. Va bene per documentazione, ma il DDL include anche una funzione trigger `fn_seed_tenant_config()` (schema riga 522) che è la vera soluzione. L'inconsistenza può confondere gli sviluppatori.
**Raccomandazione:** Rimuovere gli INSERT con tenant-123 dalla tech spec e lasciare solo il trigger come reference implementation. Oppure marcare chiaramente come "esempio per documentazione, non eseguire".

### H4: Missing endpoint per pipeline stages PATCH
**File:** tech-spec — M2 API endpoints
**Problema:** C'è POST per creare stadio, ma manca PATCH per modificare/riordinare stadi esistenti. La story US-136 richiede che admin possa gestire stadi pre-funnel.
**Raccomandazione:** Aggiungere `PATCH /api/v1/crm/pipeline/stages/{stage_id}` e `PUT /api/v1/crm/pipeline/stages/reorder` (per drag-and-drop riordinamento).

### H5: N+1 risk su compensation calculation
**File:** tech-spec BR-P8.11 (righe 612-623)
**Problema:** L'algoritmo di calcolo compensi itera per ogni user → per ogni deal → per ogni rule. Con 50 user, 200 deal e 10 regole, sono potenzialmente 100k iterazioni con query separate.
**Raccomandazione:** Pre-aggregare deal revenue per user con una singola query CTE, poi applicare le regole in-memory. Aggiungere indice `(tenant_id, assigned_to, is_won, closed_at)` su crm_deals per la query di aggregazione.

---

## MEDIUM Issues

### M1: `crm_deal_products` UNIQUE constraint troppo restrittivo
**File:** schema (riga 281), stories AC-144.4
**Problema:** Il DDL ha `UNIQUE (tenant_id, deal_id, product_id)`, ma la story AC-144.4 dice esplicitamente "il sistema consente di aggiungere la stessa linea di prodotto (potrebbe essere multiple phase)".
**Fix:** Rimuovere il UNIQUE constraint, oppure adattare la story. Se si mantiene il UNIQUE, la UI deve offrire "modifica quantità" invece di "aggiungi duplicato". Raccomando: rimuovere UNIQUE, aggiungere campo `phase` o `line_number` per distinguere righe multiple dello stesso prodotto.

### M2: `user_type` enum manca `'system'` per service accounts
**File:** schema (riga 398)
**Problema:** L'enum user_type ha `('internal', 'external', 'admin')` ma manca un tipo per service accounts (es. il cron job dei compensi, che ha `created_by = 'system'` nelle compensation_entries). Il campo `created_by VARCHAR(100)` in compensation_entries accetta "system" come stringa ma non è un user.
**Raccomandazione:** O aggiungere `'system'` all'enum user_type e creare un user di sistema per audit trail, oppure rendere `user_id` nullable in compensation_entries per calcoli automatici.

### M3: Audit log — GDPR retention non implementato a livello DDL
**File:** tech-spec riga 644: "Log retention per 90 gg (configurabile)"
**Problema:** Non c'è nessun meccanismo DDL o cron per la retention (delete records > 90 gg). Dato che il trigger impedisce DELETE, serve una soluzione.
**Raccomandazione:** Il trigger immutabilità deve avere un'eccezione per un utente sistema/cron specifico (es. `IF current_user = 'audit_gc' THEN ALLOW`), oppure usare partitioning by month e DROP PARTITION per retention.

### M4: Manca wireframe per "Utenti" (CRUD utenti esterni)
**File:** wireframes-pivot8.md — L'indice lista 10 wireframe ma nessuno copre la pagina di gestione utenti/invito utente esterno.
**Problema:** Le stories US-139 (crea utente esterno) e US-140 (canale/prodotto default) richiedono form specifiche non wireframmate.
**Fix:** Aggiungere WF-11 "Impostazioni > Utenti" con lista utenti + form nuovo utente esterno.

### M5: `default_product_id` su users — campo extra non usato nelle stories
**File:** schema (riga 407), tech-spec (riga 254)
**Problema:** La colonna `default_product_id` è aggiunta alla tabella users, ma nessuna story (US-138→111) la menziona esplicitamente come requisito di pre-selezione deal.
**Raccomandazione:** O aggiungere un AC nella story US-140 che copra il behavior di default_product_id, oppure rimuovere il campo se non necessario per MVP.

---

## LOW Issues

### L1: Trigger `fn_audit_log_prevent_modification` definito due volte
**File:** schema-pivot8.md (righe 189-201) vs tech-spec (righe 286-296)
**Problema:** Due definizioni diverse della stessa funzione con nomi diversi (`fn_audit_log_prevent_modification` vs `raise_immutable_error`). Confusione su quale usare.
**Fix:** Unificare il nome. Raccomando `fn_audit_log_prevent_modification` (più descrittivo).

### L2: `crm_dashboard_widgets.created_by` — ON DELETE SET NULL rischioso
**File:** schema (riga 304)
**Problema:** Se l'utente che ha creato la dashboard viene cancellato, `created_by` diventa NULL. Per dashboard condivise con il team, si perde traccia di chi l'ha creata.
**Raccomandazione:** Usare `ON DELETE RESTRICT` e gestire il caso di cancellazione utente a livello applicativo (reassign dashboard).

### L3: Export audit CSV "firmato digitalmente" — ambiguo
**File:** stories AC-141.4
**Problema:** La story dice "file CSV è firmato digitalmente (hash SHA256) per attestare integrità". SHA256 è un hash, non una firma digitale. Per firma vera serve una chiave privata.
**Fix:** Chiarire: o è un checksum SHA256 nel filename/header (non firma), oppure specificare la PKI usata per firma vera.

### L4: Manca endpoint DELETE per gestione ruoli
**File:** tech-spec M3 endpoints — C'è GET e POST per ruoli, ma manca DELETE.
**Raccomandazione:** Aggiungere `DELETE /api/v1/crm/roles/{role_id}` con validazione: non si possono eliminare ruoli sistema, non si possono eliminare ruoli con utenti assegnati (409 Conflict).

---

## Positive Observations

1. **ADR-011 eccellente** — La decisione è ben motivata con tabella comparativa e analisi di trade-off. Il pattern Config Layer → Business Logic → Data Layer è l'approccio giusto per multi-tenant configurabile.

2. **Schema DB robusto** — Tenant_id su ogni tabella, UNIQUE constraints corretti per code+tenant, soft delete con is_active, JSONB per flessibilità dove serve. Trigger immutabilità per audit log è una scelta professionale.

3. **User stories di qualità** — Ogni story ha 4+ AC con happy path, error, edge case e boundary. Il formato DATO-QUANDO-ALLORA è coerente. Le dipendenze tra stories sono chiare e corrette.

4. **Business rules enumerate** — Le 12 BR (BR-P8.1→BR-P8.12) coprono tutti i casi critici con riferimenti alle stories. Ottimo per QA testing.

5. **Wireframes completi** — 10 wireframe ASCII coprono tutte le pagine settings + pipeline + analytics + audit. La matrice permessi (WF-3.2) è particolarmente ben fatta.

6. **Migration strategy prudente** — L'approccio di mantenere il campo `source` originale per 30 giorni post-migration è una buona pratica di rollback safety.

7. **Seed data via trigger** — La funzione `fn_seed_tenant_config()` che popola origini, activity types e ruoli per ogni nuovo tenant è la soluzione giusta per multi-tenant.

---

## Riepilogo Fix Richiesti

| # | Severità | Descrizione | File |
|---|----------|-------------|------|
| C1 | CRITICAL | Allineare `is_prefunnel` → `stage_type` nella story US-136 | stories |
| C2 | CRITICAL | Correggere conteggio "20" → "21" stories | stories |
| C3 | CRITICAL | Migration origin_id in 2 step (nullable → backfill → constraint) | schema |
| C4 | CRITICAL | Riordinare DDL: crm_product_categories prima di crm_products | schema |
| H1 | HIGH | Validazione JSON Schema per dashboard_layout | tech-spec |
| H2 | HIGH | Rimuovere `formula` da calculation_method per MVP | tech-spec, schema |
| H3 | HIGH | Rimuovere INSERT tenant-123 o marcare come esempio | tech-spec |
| H4 | HIGH | Aggiungere PATCH/PUT per pipeline stages | tech-spec |
| H5 | HIGH | Ottimizzare compensation calc con CTE pre-aggregata | tech-spec |
| M1 | MEDIUM | Risolvere conflitto UNIQUE vs AC-144.4 (duplicati prodotto) | schema, stories |
| M2 | MEDIUM | Aggiungere user_type 'system' per service accounts | schema |
| M3 | MEDIUM | Definire meccanismo retention audit log (partition/cron) | schema |
| M4 | MEDIUM | Aggiungere wireframe gestione utenti esterni | wireframes |
| M5 | MEDIUM | Allineare default_product_id con una AC o rimuovere | schema, stories |

**Totale: 4 CRITICAL, 5 HIGH, 5 MEDIUM, 4 LOW**

I 4 CRITICAL sono quick-fix (naming, conteggio, ordine DDL, migration step). I 5 HIGH richiedono decisioni di design ma non bloccano lo sprint planning se si accettano le raccomandazioni.

---

*Review completata il 2026-04-04*
*Reviewer: Claude (Engineering Code Review)*
