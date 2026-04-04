# User Stories — Pivot 9: Gestione Utenti e Permessi Multi-Commerciale

> Data: 2026-04-04

---

## Ruoli

| Ruolo | Vede | Fa |
|-------|------|-----|
| **owner** | Tutto | Tutto + gestione utenti + impostazioni |
| **admin** | Tutto | Tutto tranne gestione billing |
| **commerciale** | Solo i propri deal/contatti assegnati | CRUD sui propri deal, invio email, attivita |
| **viewer** | Tutto (sola lettura) | Nessuna modifica |

---

### US-109: Gestione utenti — invito e ruoli
**Come** owner
**Voglio** invitare nuovi utenti, assegnare ruoli e gestire il team
**Per** dare accesso ai commerciali senza condividere le mie credenziali

**AC-109.1**: Lista utenti del tenant con nome, email, ruolo, data creazione
**AC-109.2**: Invito utente: inserisci email + ruolo → crea utente con password temporanea
**AC-109.3**: Modifica ruolo utente (owner, admin, commerciale, viewer)
**AC-109.4**: Disattiva utente (soft delete — non puo piu accedere)
**AC-109.5**: Solo owner e admin possono gestire utenti

**SP**: 5 | **Priorita**: Must Have

---

### US-110: Permessi row-level su CRM
**Come** commerciale
**Voglio** vedere solo i deal e contatti assegnati a me
**Per** non essere distratto dai deal degli altri e proteggere le informazioni

**AC-110.1**: Commerciale vede solo deal con assigned_to = proprio user_id
**AC-110.2**: Commerciale vede solo contatti con assigned_to = proprio user_id
**AC-110.3**: Owner e admin vedono tutti i deal e contatti
**AC-110.4**: Pipeline summary per owner/admin mostra tutto, per commerciale solo i propri
**AC-110.5**: Commerciale puo creare deal/contatti (auto-assegnati a se stesso)

**SP**: 5 | **Priorita**: Must Have

---

### US-111: Sender email dinamico per commerciale
**Come** commerciale
**Voglio** che le email inviate dal CRM arrivino con il mio nome e la mia email
**Per** mantenere la relazione personale con il cliente

**AC-111.1**: Ogni utente ha campi sender_email e sender_name nel profilo
**AC-111.2**: Quando un commerciale invia email, usa il suo sender (non quello globale)
**AC-111.3**: Se sender_email non configurato, usa il default globale (BREVO_SENDER_EMAIL)
**AC-111.4**: Le variabili {{commerciale}} nel template vengono sostituite con il nome dell'utente

**SP**: 3 | **Priorita**: Should Have

---

### US-112: Pagina admin gestione utenti (frontend)
**Come** owner
**Voglio** una pagina in Impostazioni per gestire il team
**Per** invitare commerciali e controllare i permessi

**AC-112.1**: Pagina /impostazioni/utenti con lista utenti
**AC-112.2**: Form invito: email, nome, ruolo (dropdown)
**AC-112.3**: Modifica ruolo inline
**AC-112.4**: Pulsante disattiva/riattiva
**AC-112.5**: Visibile solo a owner e admin

**SP**: 5 | **Priorita**: Must Have

---

## Riepilogo

| Story | SP | Priorita |
|-------|-----|----------|
| US-109 | 5 | Must |
| US-110 | 5 | Must |
| US-111 | 3 | Should |
| US-112 | 5 | Must |
| **TOTALE** | **18** | |

## Sprint Plan

| Sprint | Stories | SP |
|--------|---------|-----|
| Sprint 32 | US-109, US-110, US-111, US-112 | 18 |
