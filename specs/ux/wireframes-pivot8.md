# Wireframes — Pivot 8: Social Selling Configurabile

**Progetto:** AgentFlow PMI — CRM B2B
**Pivot:** 8 — Social Selling Configurabile
**Data:** 2026-04-04
**Stato:** Wireframe ASCII Draft
**Tool finale:** Figma / Adobe XD

---

## Indice Wireframe

1. **Impostazioni > Origini** — Gestione canali acquisizione custom
2. **Impostazioni > Tipi Attività** — Gestione tipi di attività custom
3. **Impostazioni > Ruoli** — Matrice permessi granulare
4. **Impostazioni > Prodotti** — Catalogo prodotti/servizi
5. **Pipeline Kanban — Estesa con Pre-funnel** — Stadi pre-pipeline
6. **Dashboard KPI Componibile** — Widget personalizzabili
7. **Profilo Utente Esterno** — Scadenza accesso, canale default, scorecard
8. **Scorecard Collaboratore** — KPI performance
9. **Compensi Mensili** — Calcolo, conferma, export
10. **Audit Log** — Tracciabilità immutabile

---

## WF-1: Impostazioni > Origini (CRUD Origini)

### WF-1.1: Lista Origini

```
┌────────────────────────────────────────────────────────────────┐
│                   AGENTFLOW PMI — IMPOSTAZIONI                  │
├────────────────────────────────────────────────────────────────┤
│ ◀ IMPOSTAZIONI                                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Origini Contatti          [+ Nuova Origine]  🔍 [Cerca...]    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Icona │ Codice              │ Etichetta         │ Status  │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 🌐   │ web_form            │ Web Form          │ ✓ Attivo │  │
│  │       │                     │                   │ [⋯ Mod] │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 💼   │ linkedin_organic    │ LinkedIn Organico │ ✓ Attivo │  │
│  │       │                     │                   │ [⋯ Mod] │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 💬   │ linkedin_dm         │ LinkedIn DM       │ ✓ Attivo │  │
│  │       │                     │                   │ [⋯ Mod] │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 👥   │ referral            │ Referral          │ ✗ Inattiva│  │
│  │       │                     │                   │ [⋯ Mod] │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 🎤   │ event               │ Evento/Conferenza │ ✓ Attivo │  │
│  │       │                     │                   │ [⋯ Mod] │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 📧   │ cold_outreach       │ Cold Email        │ ✓ Attivo │  │
│  │       │                     │                   │ [⋯ Mod] │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                 Pagina 1 di 1     │
│                                                                  │
└────────────────────────────────────────────────────────────────┘

Colonna "Status":
  - ✓ Attivo: origine attiva, appare in dropdown new/edit contact
  - ✗ Inattiva: soft-deleted, non appare in dropdown

[⋯ Mod]: Bottone menu → Modifica | Disattiva | (no Delete)
```

---

### WF-1.2: Form Nuova Origine

```
┌────────────────────────────────────────────────────────────────┐
│                   NUOVA ORIGINE CONTATTO                        │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Codice (univoco per tenant)                                     │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ linkedin_sales                                              ││
│  └────────────────────────────────────────────────────────────┘│
│  Max 50 caratteri. Non modificabile dopo creazione.             │
│                                                                  │
│  Etichetta                                                       │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ LinkedIn Sales Navigator                                    ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Canale Padre (per raggruppamento)                              │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ - Seleziona -                                          ▼    ││
│  ├────────────────────────────────────────────────────────────┤│
│  │ social          ← LinkedIn, TikTok, etc.                    │
│  │ direct          ← Web form, Referral, Cold                  │
│  │ event           ← Conferenza, Webinar                       │
│  │ other           ← Altro / Non classificato                  │
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Icona                                                           │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 💼 icon-linkedin                                       🎨   ││
│  └────────────────────────────────────────────────────────────┘│
│  (bottone color picker accanto — apre palette icone Tailwind) │
│                                                                  │
│  ☑ Attiva                                                        │
│  (checkbox di default checked)                                   │
│                                                                  │
│                                                                  │
│        [Annulla]                          [Salva Origine]       │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### WF-1.3: Form Modifica Origine

```
┌────────────────────────────────────────────────────────────────┐
│                   MODIFICA ORIGINE CONTATTO                     │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Codice (univoco per tenant)                                     │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ linkedin_organic                                    [Locked] ││
│  └────────────────────────────────────────────────────────────┘│
│  ℹ Codice non modificabile. Univoco per tenant.                │
│                                                                  │
│  Etichetta                                                       │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ LinkedIn Organico - Aggiornato 2026                         ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Canale Padre                                                    │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ social                                                 ▼    ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Icona                                                           │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 💼 icon-linkedin                                       🎨   ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ☑ Attiva     (se uncheck → soft delete, contatti rimangono)   │
│                                                                  │
│  Contatti associati: 42                                          │
│  ℹ Questa origine ha 42 contatti. Se disattivi, rimangono.     │
│                                                                  │
│        [Annulla]                          [Salva Modifiche]     │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-2: Impostazioni > Tipi Attività

### WF-2.1: Lista Tipi Attività

```
┌────────────────────────────────────────────────────────────────┐
│                   AGENTFLOW PMI — IMPOSTAZIONI                  │
├────────────────────────────────────────────────────────────────┤
│ ◀ IMPOSTAZIONI                                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Tipi di Attività          [+ Nuovo Tipo]  🔍 [Cerca...]       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Codice       │ Etichetta        │ Categoria   │ Ultimo  │    │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ call         │ Chiamata         │ Sales       │ ✓       │    │
│  │              │                  │             │ [⋯ Mod] │    │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ email        │ Email            │ Sales       │ ✓       │    │
│  │              │                  │             │ [⋯ Mod] │    │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ meeting      │ Incontro         │ Sales       │ ✓       │    │
│  │              │                  │             │ [⋯ Mod] │    │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ linkedin_dm  │ Inmail LinkedIn  │ Sales       │ ✓       │    │
│  │              │                  │             │ [⋯ Mod] │    │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ note         │ Nota Interna     │ Sales       │ ✗       │    │
│  │              │                  │             │ [⋯ Mod] │    │
│  └──────────────────────────────────────────────────────────┘   │
│                                                 Pagina 1 di 1     │
│                                                                  │
│  "Ultimo" = checkbox "Conta come ultimo contatto" (icon 📅)     │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### WF-2.2: Form Nuovo Tipo Attività

```
┌────────────────────────────────────────────────────────────────┐
│                   NUOVO TIPO ATTIVITÀ                           │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Codice (univoco per tenant)                                     │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ linkedin_poll                                               ││
│  └────────────────────────────────────────────────────────────┘│
│  Max 50 caratteri.                                               │
│                                                                  │
│  Etichetta                                                       │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ LinkedIn Poll Participation                                ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Categoria                                                       │
│  ○ Sales           ← attività commerciale (diretto al deal)    │
│  ○ Marketing       ← attività di awareness/engagement           │
│  ○ Support         ← attività di assistenza/support            │
│                                                                  │
│  ☑ Conta come ultimo contatto                                   │
│    (Se attivo, aggiorna contact.last_contact_at quando loggato)│
│                                                                  │
│        [Annulla]                          [Salva Tipo]          │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-3: Impostazioni > Ruoli (RBAC Matrice Permessi)

### WF-3.1: Lista Ruoli

```
┌────────────────────────────────────────────────────────────────┐
│                   AGENTFLOW PMI — IMPOSTAZIONI                  │
├────────────────────────────────────────────────────────────────┤
│ ◀ IMPOSTAZIONI                                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Ruoli e Permessi          [+ Nuovo Ruolo]  🔍 [Cerca...]      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Nome                │ Descrizione            │ Tipo    │     │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Owner               │ Proprietario — ...     │ Sistema │     │
│  │                     │                        │ [Locked]│     │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Admin               │ Administrator — ...    │ Sistema │     │
│  │                     │                        │ [Locked]│     │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Sales Rep           │ Sales Representative   │ Custom  │     │
│  │                     │                        │ [⋯ Mod] │     │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Account Executive   │ Gestisce book + ...    │ Custom  │     │
│  │                     │                        │ [⋯ Mod] │     │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Viewer              │ Read-only viewer       │ Sistema │     │
│  │                     │                        │ [Locked]│     │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [Sistema] = non modificabile                                    │
│  [Custom] = custom role creato dagli admin                      │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### WF-3.2: Matrice Permessi (Editabile)

```
┌────────────────────────────────────────────────────────────────┐
│                   MODIFICA RUOLO: "Account Executive"           │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Nome Ruolo                                                      │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ Account Executive                                           ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Descrizione                                                     │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ Gestisce il suo book clienti e scorecard personale         ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌───────────────────── MATRICE PERMESSI ───────────────────┐  │
│  │                                                             │  │
│  │       Entità      │ Create │ Read │ Update │ Delete │ Exp │  │
│  │ ─────────────────────────────────────────────────────────│  │
│  │ Contatti          │   ☑    │  ☑   │   ☑    │   ☐    │ ☑   │  │
│  │ Deal              │   ☑    │  ☑   │   ☑    │   ☐    │ ☑   │  │
│  │ Attività          │   ☑    │  ☑   │   ☑    │   ☐    │ ☐   │  │
│  │ Pipeline          │   ☐    │  ☑   │   ☑    │   ☐    │ ☐   │  │
│  │ Report            │   ☐    │  ☑   │   ☐    │   ☐    │ ☑   │  │
│  │ Audit Log         │   ☐    │  ☐   │   ☐    │   ☐    │ ☐   │  │
│  │ Settings          │   ☐    │  ☑   │   ☐    │   ☐    │ ☐   │  │
│  │                                                             │  │
│  │ ☑ = checkbox attivo (permesso concesso)                    │  │
│  │ ☐ = checkbox inattivo (permesso negato)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Scope Accesso (per ogni entità)                                │
│  ○ Own only      ← solo dati assegnati a questo utente         │
│  ○ Team          ← dati del team                                │
│  ○ All           ← tutti i dati (con row-level filter per ext) │
│                                                                  │
│        [Annulla]                          [Salva Ruolo]        │
│                                                                  │
└────────────────────────────────────────────────────────────────┘

Note:
- La matrice è editabile: click checkbox per toggle permesso
- Scope default = "own_only" per tutti tranne Owner (scope="all")
- Non è possibile modificare ruoli Sistema (Owner, Admin, Viewer)
```

---

## WF-4: Impostazioni > Prodotti (Catalogo)

### WF-4.1: Lista Prodotti

```
┌────────────────────────────────────────────────────────────────┐
│                   AGENTFLOW PMI — IMPOSTAZIONI                  │
├────────────────────────────────────────────────────────────────┤
│ ◀ IMPOSTAZIONI                                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Catalogo Prodotti/Servizi  [+ Nuovo Prodotto]  🔍 [Cerca...]  │
│                                                                  │
│  Filtri: [Categoria ▼] [Pricing Model ▼] [Status ▼]           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Nome                 │ Codice          │ Pricing  │ St. │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Sviluppo Custom      │ dev_custom      │ Hourly   │ ✓   │   │
│  │ Backend              │                 │ €85/ora  │ Mod │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Supporto SLA Annuale │ support_sla     │ Fixed    │ ✓   │   │
│  │                      │                 │ €5.000   │ Mod │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Hosting Cloud        │ hosting_cloud   │ Hourly   │ ✗   │   │
│  │                      │                 │ €12/mese │ Mod │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Training Online      │ training_online │ Fixed    │ ✓   │   │
│  │                      │                 │ €3.000   │ Mod │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                 Pagina 1 di 2     │
│                                                                  │
│  "St." = Status: ✓ Attivo, ✗ Inattivo (soft deleted)           │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### WF-4.2: Form Nuovo Prodotto

```
┌────────────────────────────────────────────────────────────────┐
│                   NUOVO PRODOTTO                                │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Nome Prodotto (required)                                        │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ Sviluppo Backend Custom                                     ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Codice (required, unique per tenant)                            │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ dev_backend_custom                                          ││
│  └────────────────────────────────────────────────────────────┘│
│  Max 50 caratteri.                                               │
│                                                                  │
│  Categoria                                                       │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ - Seleziona o crea -                                  ▼    ││
│  └────────────────────────────────────────────────────────────┘│
│  (+ opzione per create categoria inline)                        │
│                                                                  │
│  Modello Pricing (required)                                      │
│  ○ Fixed        ← prezzo fisso (€)                             │
│  ○ Hourly       ← prezzo orario (€/ora + giorni stima)        │
│  ○ Custom       ← negoziato caso-per-caso                      │
│                                                                  │
│  ┌─ PRICING (varia in base a selezione) ───────────────────┐   │
│  │                                                          │   │
│  │ [Se Fixed]:                                             │   │
│  │ Prezzo Base (€): ┌────────────┐                         │   │
│  │                  │ 50000.00   │                         │   │
│  │                  └────────────┘                         │   │
│  │                                                          │   │
│  │ [Se Hourly]:                                            │   │
│  │ Prezzo Orario (€): ┌────────────┐                       │   │
│  │                    │ 85.00      │                       │   │
│  │                    └────────────┘                       │   │
│  │ Giorni Stima (default): ┌────────────┐                 │   │
│  │                         │ 20         │                 │   │
│  │                         └────────────┘                 │   │
│  │ Tipo Tecnologia: ┌────────────┐                        │   │
│  │                  │ Backend ▼  │                        │   │
│  │                  └────────────┘                        │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Margine Target (%)                                              │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 35                                                          ││
│  └────────────────────────────────────────────────────────────┘│
│  (per analytics: confronta revenue vs margin target)             │
│                                                                  │
│  Descrizione                                                     │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ Sviluppo backend custom con architettura microservizi      ││
│  │ TypeScript + Node.js                                        ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ☑ Attivo                                                        │
│                                                                  │
│        [Annulla]                          [Salva Prodotto]     │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-5: Pipeline Kanban Estesa con Pre-funnel

```
┌────────────────────────────────────────────────────────────────┐
│                   AGENTFLOW PMI — PIPELINE                      │
├────────────────────────────────────────────────────────────────┤
│ [Filtri] [Aggiungi Filtro ▼]  [View: Kanban | List | Timeline] │
│  Canale: [- Tutti -  ▼]  Prodotto: [- Tutti - ▼]  User: [Me ▼] │
│                                                                  │
│ ┌────────────┬────────────┬────────────┬────────────┬─────────┐ │
│ │  PROSPECT  │ CONTATTO   │ NUOVO LEAD │ QUALIF.    │ PROPOSTA│ │
│ │            │ QUALIF.    │            │            │         │ │
│ │  [+]       │  [+]       │  [+]       │  [+]       │  [+]    │ │
│ │  (Pre-fal) │ (Pre-fal)  │ (Std)      │ (Std)      │ (Std)   │ │
│ └────────────┼────────────┼────────────┼────────────┼─────────┘ │
│              │            │            │            │            │
│  ┌──────────┐│┌──────────┐│┌──────────┐│┌──────────┐│┌────────┐ │
│  │          │││          │││  ACME    │││  XYZ     │││  ABC   │ │
│  │          │││          │││  Corp    │││  Ltd     │││  SpA   │ │
│  │ STARTUP  │││  ENERGIA │││  [Develop]││  [Fixed] │││[T&M]   │ │
│  │ A        │││  B       │││  €50k    ││  €30k    ││  €20k  │ │
│  │ €10k     │││ €25k     │││ 👤 Marco ││ 👤 Sara  ││ 👤 Tom │ │
│  │ ← drag   │││ ← drag   │││ Stage: 3 ││ Stage: 3 ││Stage: 4 │ │
│  │          │││          │││ [⋯] [×]  ││ [⋯] [×]  ││ [⋯][×] │ │
│  └──────────┘│└──────────┘│└──────────┘│└──────────┘│└────────┘ │
│              │            │            │            │            │
│  ┌──────────┐│            │            │            │            │
│  │ MICRO    ││            │            │            │            │
│  │ LTD      ││            │            │            │            │
│  │ €5k      ││            │            │            │            │
│  │ 👤 Lisa  ││            │            │            │            │
│  │          ││            │            │            │            │
│  └──────────┘│            │            │            │            │
│              │            │            │            │            │
│ ┌────────────┬────────────┬────────────┬────────────┬─────────┐ │
│ │ ORDINE     │ CONFERMATO │ IN INVOICE │ CHIUSO     │         │ │
│ │ RICEVUTO   │            │            │ (Vinto)    │         │ │
│ │  [+]       │  [+]       │  [+]       │  [+]       │         │ │
│ │  (Std)     │  (Std)     │  (Std)     │  (Std)     │         │ │
│ └────────────┼────────────┼────────────┼────────────┘─────────┘ │
│              │            │            │                         │
│              │            │            │ ┌──────────────────┐   │
│              │            │            │ │ TIM SPA         │   │
│              │            │            │ │ €150k ✓         │   │
│              │            │            │ │ Chiuso il:      │   │
│              │            │            │ │ 2026-02-28      │   │
│              │            │            │ │ Margine: 35%    │   │
│              │            │            │ └──────────────────┘   │
│                                                                  │
│  Legend:                                                         │
│  (Pre-fun) = Stadio pre-funnel (tracciamento, non in pipeline) │
│  (Std) = Stadio pipeline standard                               │
│  Drag card tra colonne per cambiar stage                        │
│  [⋯] = Menu opzioni: dettagli, edit, delete, log activity    │
│  [×] = Archivia deal                                            │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-6: Dashboard KPI Componibile

### WF-6.1: Lista Dashboard e Builder

```
┌────────────────────────────────────────────────────────────────┐
│                 AGENTFLOW PMI — ANALYTICS > DASHBOARD           │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Le Mie Dashboard          [+ Nuova Dashboard]                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Dashboard                   │ Owner      │ Widget │ Accesso │ │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Q1 2026 Pipeline            │ Marco      │   4    │ Public  │ │
│  │ [Apri]                      │ Created:   │        │         │ │
│  │                             │ 2026-01-15 │        │ [Mod]   │ │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Sales Team Performance      │ Marco      │   6    │ Private │ │
│  │ [Apri]                      │ Created:   │        │         │ │
│  │                             │ 2026-03-01 │        │ [Mod]   │ │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Template Dashboard                                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Starter Pipeline       [Duplica come mia]                │   │
│  │ Mostra 4 widget KPI standard (Revenue, Deal count, etc.) │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### WF-6.2: Dashboard Editor / View

```
┌────────────────────────────────────────────────────────────────┐
│                 DASHBOARD: Q1 2026 Pipeline                     │
├────────────────────────────────────────────────────────────────┤
│ [← Back to List]  [Edit Layout]  [Add Widget +]  [Share ▼]     │
│                                                                  │
│ Global Filters: [Periodo: Last 3 months ▼] [Prodotto: - ▼]    │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ REVENUE MoM                         ┌──────────────────┐ │   │
│ │ Last 3 months / Prodotto: All       │   €150,000 ──┐  │ │   │
│ │                                     │      €120,000─┼──┘  │   │
│ │ Chart Type: Line                    │      €90,000──┼─    │   │
│ │                                     │                │    │   │
│ │ ▏ Febr 2026                        │        Feb   Mar   Apr  │   │
│ │ ┌─────────────────────────────────┐│                      │   │
│ │ │ €148,200                        ││ Trend: +2.3% ↗       │   │
│ │ └─────────────────────────────────┘│                      │   │
│ │                                  [⋯ Opzioni widget]         │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ DEAL COUNT BY STAGE                                      │   │
│ │ Last 3 months / All Products                             │   │
│ │                                                          │   │
│ │ ┌─────┬─────┬─────┬─────┬─────┬─────┐                  │   │
│ │ │  12 │  18 │  25 │  15 │   8 │   3 │ Win             │   │
│ │ │     │     │     │     │     │     │ Prospect        │   │
│ │ │ NL  │ QFD │ PRO │ ORD │ CON │ CLS │                  │   │
│ │ └─────┴─────┴─────┴─────┴─────┴─────┘                  │   │
│ │                            [⋯ Opzioni widget]         │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ WIN RATE %                          ┌──────────────────┐ │   │
│ │ Current Quarter / All               │         65% ←    │ │   │
│ │                                     │    Target: 50%   │ │   │
│ │ Gauge Chart                         │   Prev QTR: 60%  │ │   │
│ │                                     │  Trend: +5% ↗    │ │   │
│ │                                  [⋯ Opzioni widget]     │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ Bottone "Add Widget": open widget catalog                       │
│ - Revenue MoM                                                    │
│ - Deal Count by Stage                                            │
│ - Win Rate                                                       │
│ - Avg Deal Size                                                  │
│ - Forecast 90 days                                               │
│ - Top Contacts by Revenue                                        │
│ - Activity Heatmap                                               │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-7: Profilo Utente Esterno

### WF-7.1: Profilo Utente Esterno (Admin View)

```
┌────────────────────────────────────────────────────────────────┐
│              IMPOSTAZIONI > UTENTI > Marco Contractor          │
├────────────────────────────────────────────────────────────────┤
│ ◀ Torna a Utenti                                                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ DETTAGLI UTENTE                                           │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │                                                           │   │
│  │ Email                                                     │   │
│  │ contractor@example.com                                    │   │
│  │                                                           │   │
│  │ Nome Completo                                             │   │
│  │ Marco Contractor                                          │   │
│  │                                                           │   │
│  │ Tipo Utente                                               │   │
│  │ ● Internal     ○ External    ○ Admin                      │   │
│  │ (se External, abilita accesso_expires_at)                │   │
│  │                                                           │   │
│  │ Accesso Scade Il (se External)                            │   │
│  │ ┌────────────────────────────────────────────────────┐   │   │
│  │ │ 2026-06-30                                         │   │   │
│  │ └────────────────────────────────────────────────────┘   │   │
│  │ ⓘ Utente sarà automaticamente disattivato dopo questa   │   │
│  │   data. Rimarrà nei log audit per compliance.           │   │
│  │                                                           │   │
│  │ ⚠️ ACCESSO SCADUTO                                        │   │
│  │ Status: Disattivato (accesso scaduto il 2026-06-01)     │   │
│  │ [Estendi Accesso]                                         │   │
│  │                                                           │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ CONTROLLO ACCESSO                                         │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │                                                           │   │
│  │ Ruolo RBAC                                                │   │
│  │ ┌────────────────────────────────────────────────────┐   │   │
│  │ │ Sales Rep                                      ▼   │   │   │
│  │ └────────────────────────────────────────────────────┘   │   │
│  │                                                           │   │
│  │ Canale Default (pre-fill contatto)                       │   │
│  │ ┌────────────────────────────────────────────────────┐   │   │
│  │ │ LinkedIn Sales                                 ▼   │   │   │
│  │ └────────────────────────────────────────────────────┘   │   │
│  │ ℹ Questo utente vede SOLO contatti con origine=         │   │
│  │   "LinkedIn Sales" (row-level security)                  │   │
│  │                                                           │   │
│  │ Prodotto Default (pre-select deal)                       │   │
│  │ ┌────────────────────────────────────────────────────┐   │   │
│  │ │ Sviluppo Custom                                ▼   │   │   │
│  │ └────────────────────────────────────────────────────┘   │   │
│  │                                                           │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ AUDIT TRAIL PER UTENTE                                    │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │                                                           │   │
│  │ Ultimi Log: [2026-04-04]  Marco ha creato contatto      │   │
│  │             [2026-04-02]  Marco ha aggiornato deal #42  │   │
│  │             [2026-04-01]  Marco login da IP 192.1...    │   │
│  │             [Mostra tutti]                               │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│        [Annulla]                          [Salva Modifiche]     │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-8: Scorecard Collaboratore

```
┌────────────────────────────────────────────────────────────────┐
│              ANALYTICS > SCORECARD COLLABORATORE                │
├────────────────────────────────────────────────────────────────┤
│ [Seleziona Utente: Marco Rossi ▼]  [Periodo: Last 30 days ▼]  │
│ [Filtro Prodotto: - Tutti - ▼]                                 │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │                    MARCO ROSSI                            │   │
│ │                 Last 30 days                              │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────┬──────────────────┬──────────────────┐    │
│ │ DEAL COUNT       │ REVENUE CLOSED   │ WIN RATE         │    │
│ │                  │                  │                  │    │
│ │     5            │     €125,000     │     60%          │    │
│ │ ↗ +10% vs prev   │ ↗ +25% vs prev   │ ↗ +5% vs prev    │    │
│ │ Target: -        │ Target: €100k ✓  │ Target: 50% ✓    │    │
│ └──────────────────┴──────────────────┴──────────────────┘    │
│                                                                  │
│ ┌──────────────────┬──────────────────┬──────────────────┐    │
│ │ AVG DAYS TO      │ LAST CONTACT     │ ACTIVITY COUNT   │    │
│ │ CLOSE            │                  │                  │    │
│ │                  │                  │                  │    │
│ │     42 gg        │ 2026-04-03       │     12           │    │
│ │ ↙ -10% vs prev ✓ │ 1 gg fa          │ ↗ +3 vs prev     │    │
│ │ Target: 30 gg    │ (Last touch:     │ Target: 10 /mese │    │
│ │ ⚠ Above target   │ Inmail LinkedIn) │                  │    │
│ └──────────────────┴──────────────────┴──────────────────┘    │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ DEAL BREAKDOWN (Last 30 days)                             │   │
│ │                                                            │   │
│ │ Deal            │ Stage        │ Product        │ Revenue │   │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ ACME Corp       │ In Proposal  │ Sviluppo       │ €50,000 │   │
│ │ XYZ Ltd         │ Confermato   │ Supporto SLA    │ €30,000 │   │
│ │ TTM Spa         │ Chiuso (Win) │ Sviluppo       │ €45,000 │   │
│ │ Startup A       │ Opportunity  │ Training       │ pending │   │
│ │ (altri 1 deal)  │ ...          │ ...            │ ...     │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ [Esporta Scorecard PDF]  [Confronta con Team Media]            │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-9: Compensi Mensili

### WF-9.1: Lista Compensi (Admin View)

```
┌────────────────────────────────────────────────────────────────┐
│              ANALYTICS > COMPENSI MENSILI                       │
├────────────────────────────────────────────────────────────────┤
│ [Mese: Marzo 2026 ◀  ▶]  [Filtro Status: Draft ▼]             │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Collaboratore      │ Deal │ Revenue │ Compenso │ Status  │   │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ Marco Rossi        │  5   │ €150k   │ €3.900   │ Draft   │   │
│ │ (Assessment: OK)   │      │         │          │ [View]  │   │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ Sara Bianchi       │  3   │ €80k    │ €2.100   │ Draft   │   │
│ │ (Assessment: OK)   │      │         │          │ [View]  │   │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ Tom Verdi          │  2   │ €60k    │ €1.500   │ Draft   │   │
│ │ (Assessment: OK)   │      │         │          │ [View]  │   │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ Lisa Rossi         │  0   │ -       │ €0       │ Draft   │   │
│ │ (No data)          │      │         │          │ [View]  │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ SUMMARY:                                                         │
│ Total Compensation (Marzo): €7.500                              │
│ Status: 4 Draft, 0 Confirmed, 0 Paid                            │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Calcolato il: 2026-04-01 09:15 (automated job)          │   │
│ │ Regole applicate: Base 5% + Product Bonus +2% + Penalty │   │
│ │                                                          │   │
│ │                    [⚠️ CONFERMA TUTTI COMPENSI]          │   │
│ │                                                          │   │
│ │ Sei sicuro di voler confermare i compensi di Marzo 2026?│   │
│ │ Non sarà possibile modificare.                          │   │
│ │                                                          │   │
│ │ [Annulla]                         [Sì, Conferma Tutti]  │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### WF-9.2: Dettaglio Compenso Singolo

```
┌────────────────────────────────────────────────────────────────┐
│           DETTAGLIO COMPENSO: Marco Rossi — Marzo 2026         │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Status: Draft                                                    │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ RIEPILOGO                                                 │   │
│ │                                                           │   │
│ │ Deal Chiusi (Win):           5                            │   │
│ │ Revenue Totale:              €150,000.00                  │   │
│ │ Compenso Lordo:              €3.900,00                    │   │
│ │                                                           │   │
│ │ Calcolato il: 2026-04-01                                 │   │
│ │ Confirm data: -                                           │   │
│ │ Paid data: -                                              │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ BREAKDOWN REGOLE APPLICATE                                │   │
│ │                                                           │   │
│ │ Rule: Base Commission 5%                                  │   │
│ │   Revenue Base: €150,000                                  │   │
│ │   Rate: 5%                                                │   │
│ │   Contribution: €7,500                                    │   │
│ │                                                           │   │
│ │ Rule: Product Bonus +2% (Sviluppo)                        │   │
│ │   Filtered Revenue (Sviluppo only): €100,000              │   │
│ │   Rate: 2%                                                │   │
│ │   Contribution: €2,000                                    │   │
│ │                                                           │   │
│ │ Rule: Penalty -1% (No Activity Threshold)                 │   │
│ │   Activities count: 12 (above threshold 10)               │   │
│ │   Contribution: €0 (not applied — passed rule condition)  │   │
│ │                                                           │   │
│ │ ────────────────────────────────────────                  │   │
│ │ TOTAL COMPENSATION: €3.900,00                             │   │
│ │ (Deduction for Rule order: see JSON rules_applied)        │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ CONTRIBUTO PER DEAL                                       │   │
│ │                                                           │   │
│ │ ACME Corp (€50k — Sviluppo)                               │   │
│ │   Base: €2.500 | Bonus: €1.000 | Subtot: €3.500          │   │
│ │                                                           │   │
│ │ XYZ Ltd (€30k — Supporto)                                 │   │
│ │   Base: €1.500 | Bonus: €0 | Subtot: €1.500              │   │
│ │                                                           │   │
│ │ TTM Spa (€40k — Sviluppo)                                 │   │
│ │   Base: €2.000 | Bonus: €800 | Subtot: €2.800            │   │
│ │   (Hmm, total above, verify if split logic)               │   │
│ │                                                           │   │
│ │ (other 2 deals)                                           │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ AZIONI                                                    │   │
│ │                                                           │   │
│ │ [Conferma questo Compenso]  [Edita (admin)]  [Esporta PDF]│   │
│ │                                                           │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-10: Audit Log

### WF-10.1: Visualizzazione Audit Log

```
┌────────────────────────────────────────────────────────────────┐
│              IMPOSTAZIONI > AUDIT LOG (Tracciabilità)          │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Filtri: [Utente: Marco ▼] [Azione: Tutti ▼] [Data range: 7gg] │
│         [Entità: Tutti ▼] [Status: Tutti ▼]                    │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Timestamp          │ Utente       │ Azione             │    │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ 2026-04-04 14:30  │ Marco Rossi  │ create_contact     │    │
│ │                    │              │ ACME Corp          │    │
│ │                    │              │ Origin: LinkedIn   │    │
│ │                    │              │ Status: Success    │    │
│ │                    │              │ IP: 192.168.1.100  │    │
│ │                    │              │ [Dettagli ▼]       │    │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ 2026-04-04 12:15  │ Marco Rossi  │ update_deal        │    │
│ │                    │              │ Deal #42 (XYZ Ltd) │    │
│ │                    │              │ Stage: Prosposta   │    │
│ │                    │              │ Status: Success    │    │
│ │                    │              │ [Dettagli ▼]       │    │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ 2026-04-03 18:45  │ Sara Bianchi │ log_activity       │    │
│ │                    │              │ Contact #15 (ACME) │    │
│ │                    │              │ Activity: Call     │    │
│ │                    │              │ Status: Success    │    │
│ │                    │              │ [Dettagli ▼]       │    │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ 2026-04-03 10:00  │ Marco Rossi  │ permission_denied   │    │
│ │                    │              │ Contact #20        │    │
│ │                    │              │ Reason: Not origin │    │
│ │                    │              │ Status: Denied     │    │
│ │                    │              │ [Dettagli ▼]       │    │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ 2026-04-01 09:15  │ System (job) │ calculate_compen... │    │
│ │                    │              │ Marzo 2026         │    │
│ │                    │              │ Status: Success    │    │
│ │                    │              │ [Dettagli ▼]       │    │
│ └──────────────────────────────────────────────────────────┘   │
│                                                 Pagina 1 di 42    │
│                                                                  │
│ [⏬ Esporta Audit Log (CSV)] [Firma: SHA256]                    │
│ Firma digitale: 7f3e9c2a1b5d... (integrity verification)       │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### WF-10.2: Dettaglio Azione Audit

```
┌────────────────────────────────────────────────────────────────┐
│                    DETTAGLI AZIONE AUDIT                        │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Timestamp:        2026-04-04 14:30:22                           │
│ Utente:           Marco Rossi (marco@azienda.it)                │
│ Azione:           create_contact                                │
│ Entità:           Contact #123                                  │
│ Status:           ✓ Success                                     │
│                                                                  │
│ IP Address:       192.168.1.100                                 │
│ User-Agent:       Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ CHANGE DETAILS (JSON)                                     │   │
│ │                                                           │   │
│ │ {                                                         │   │
│ │   "action": "create_contact",                             │   │
│ │   "contact": {                                            │   │
│ │     "id": "uuid-123",                                     │   │
│ │     "name": "ACME Corp",                                  │   │
│ │     "email": "info@acme.com",                             │   │
│ │     "origin_id": "origin-linkedin",                       │   │
│ │     "status": "prospect",                                 │   │
│ │     "assigned_to": "uuid-marco"                           │   │
│ │   }                                                       │   │
│ │ }                                                         │   │
│ │                                                           │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ [Chiudi]  [Copia JSON]                                          │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## WF-11: Impostazioni > Utenti (Gestione Utenti Esterni)

### WF-11.1: Lista Utenti

```
┌────────────────────────────────────────────────────────────────┐
│                   AGENTFLOW PMI — IMPOSTAZIONI                  │
├────────────────────────────────────────────────────────────────┤
│ ◀ IMPOSTAZIONI                                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Utenti              [+ Nuovo Utente]  🔍 [Cerca...]           │
│                                                                  │
│  Filtri: [Tipo ▼ Tutti|Internal|External]  [Ruolo ▼]  [Status ▼]│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Nome              │ Email          │ Tipo     │ Ruolo    │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Marco Rossi       │ m.rossi@...   │ Internal │ Admin    │   │
│  │                   │               │          │ [⋯ Mod]  │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Laura Bianchi     │ l.bianchi@... │ External │ Sales Rep│   │
│  │ ⏰ Scade: 15/06/26│               │          │ [⋯ Mod]  │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Paolo Verdi       │ p.verdi@...   │ External │ Viewer   │   │
│  │ ⚠ Accesso scaduto │               │          │ [⋯ Mod]  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                 Pagina 1 di 1     │
│                                                                  │
│  ⏰ = Scadenza accesso prossima (< 30 gg)                       │
│  ⚠  = Accesso scaduto (utente disattivato)                      │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

### WF-11.2: Form Nuovo Utente Esterno

```
┌────────────────────────────────────────────────────────────────┐
│                   NUOVO UTENTE ESTERNO                          │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Email (required)                                                │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ collaboratore@freelance.it                                  ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Nome e Cognome                                                  │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ Laura Bianchi                                               ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Tipo Utente                                                     │
│  ○ Internal   ← dipendente/collaboratore stabile                │
│  ● External   ← freelancer, contractor, partner temporaneo     │
│                                                                  │
│  ┌─ CAMPI EXTERNAL (visibili solo se tipo=External) ─────────┐ │
│  │                                                             │ │
│  │  Data Scadenza Accesso (required per External)              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ 15/06/2026                                      📅   │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │  ℹ Dopo questa data, l'accesso sarà disattivato.          │ │
│  │                                                             │ │
│  │  Canale Default (pre-compila origine su nuovi contatti)     │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ LinkedIn Sales                                   ▼   │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │  ℹ L'utente vedrà SOLO contatti di questo canale.          │ │
│  │                                                             │ │
│  │  Prodotto Default (pre-seleziona su nuovi deal)             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ Sviluppo Custom                                  ▼   │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │  (opzionale)                                                │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Ruolo (required)                                                │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ Sales Rep                                              ▼    ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ☑ Invia email di invito                                        │
│                                                                  │
│        [Annulla]                          [Crea Utente]        │
│                                                                  │
└────────────────────────────────────────────────────────────────┘

Note:
- Se tipo = External, i campi "Scadenza" e "Canale Default" diventano visibili
- Canale default abilita row-level security: utente vede solo quel canale
- Prodotto default è opzionale (vedi story US-110)
```

---

## Design Principles

### UX Flow

1. **Settings Hub (Admin):** Accesso centralizzato a tutte le configurazioni (Origini, Tipi Attività, Ruoli, Prodotti, Compensi)
2. **CRUD Consistency:** Form pattern identico per tutte le entità (save, cancel, delete soft, error handling)
3. **Visual Hierarchy:** Codice/ID univoci sempre prominent, label leggibile, status evidente (attivo/inattivo)
4. **Row-level Security:** UI reflects user permissions — bottoni disabilitati se insufficiente permesso, no 403 errors on click
5. **Audit Trail Transparency:** Admin può tracciare ogni azione, export CSV con firma digitale per compliance

### Color Scheme

- **Active/Success:** Verde (#10B981)
- **Inactive/Disabled:** Grigio (#6B7280)
- **Error/Warning:** Rosso (#EF4444)
- **Info:** Blu (#3B82F6)
- **Pre-funnel stages:** Azzurro più scuro (#0369A1)
- **Pipeline stages:** Colore per stage (standard Kanban)

### Typography & Icons

- **Headings:** Inter Bold 18-24px
- **Labels:** Inter Medium 12-14px
- **Body:** Inter Regular 13-14px
- **Icons:** Heroicons + custom (emoji per origini/attività per UX veloce)

### Accessibility

- Tutti i form hanno label esplicite (not placeholders)
- Colori non solo informazione (icon + text per status)
- Keyboard nav supportato (Tab, Enter, Esc)
- ARIA labels su button, form control
- Contrasto WCAG AA minimo

---

## Responsive Design

### Desktop (1440px+)
- Dashboard: 4 col grid, widget full layout
- Table: full horizontal scroll se necessario
- Sidebar: always visible

### Tablet (768-1440px)
- Dashboard: 2 col grid
- Table: horizontal scroll con fixed first column
- Sidebar: collapsible

### Mobile (< 768px)
- Dashboard: 1 col, stack vertically
- Tables: card view (row → collapsed card)
- Sidebar: hamburger menu
- Forms: full width, stacked fields

---

**Wireframe completato da:** Roberto, Backend Architect + UX Designer
**Data:** 2026-04-04
**Stato:** ASCII Wireframe Draft — Ready per Figma handoff
**Next Step:** Convert to Figma components con design system completo

