# User Stories — Integrazione Calendario Commerciali
**AgentFlow PMI — CRM B2B per PMI italiane**

---

## Overview

Integrazione calendario per commerciali: vista agenda nel CRM, export .ics, sync push Microsoft 365, link Calendly.

**Principio:** AgentFlow e la source of truth delle attivita. Il calendario esterno e una **view** slave, one-way push. Nessun sync engine bidirezionale.

---

## US-151: Vista calendario attivita pianificate

**Come** commerciale
**Voglio** visualizzare tutte le mie attivita pianificate in una vista calendario (settimana/mese)
**Per** avere un colpo d'occhio sulla mia agenda e organizzare la giornata

**AC-151.1 (Happy Path)**: DATO che ho 5 attivita pianificate questa settimana, QUANDO apro `/crm/calendario`, ALLORA:
  - Vedo una vista settimanale con blocchi colorati per tipo (blu=call, verde=meeting, viola=email, grigio=task)
  - Ogni blocco mostra: soggetto, orario, nome contatto/azienda
  - Posso cambiare vista: settimana / mese / giorno
  - Le attivita completate appaiono con opacita ridotta

**AC-151.2 (Click dettaglio)**: DATO che clicco su un blocco attivita, ALLORA:
  - Si apre un popover con: soggetto, tipo, contatto, deal, descrizione, data/ora
  - Bottoni: "Completa", "Aggiungi al calendario" (.ics), "Vai al deal"

**AC-151.3 (Filtri)**: DATO che ho attivita di 3 commerciali, QUANDO sono admin, ALLORA:
  - Posso filtrare per: utente assegnato, tipo attivita, stato
  - Se sono commerciale, vedo solo le mie attivita (row-level)

**AC-151.4 (Empty state)**: DATO che non ho attivita pianificate, ALLORA:
  - Il calendario mostra messaggio "Nessuna attivita pianificata" con CTA "Pianifica la prima attivita"

**SP**: 5 | **Priorita**: Must Have | **Dipendenze**: Nessuna

---

## US-152: Export attivita come file .ics

**Come** commerciale
**Voglio** scaricare un file .ics di un'attivita pianificata
**Per** aggiungerla manualmente al mio calendario (Google, Outlook, Apple) con un click

**AC-152.1 (Happy Path)**: DATO che ho un'attivita "Call con ACME" pianificata per domani alle 10:00, QUANDO clicco "Aggiungi al calendario", ALLORA:
  - Si scarica un file `call-acme-2026-04-07.ics`
  - Il file contiene: VCALENDAR > VEVENT con DTSTART, DTEND (default +30min), SUMMARY, DESCRIPTION, ORGANIZER
  - Aprendolo su qualsiasi client calendario (Google, Outlook, Apple), l'evento viene importato

**AC-152.2 (Campi ICS)**: DATO che l'attivita ha soggetto, descrizione e contatto associato, ALLORA:
  - SUMMARY = soggetto
  - DESCRIPTION = descrizione + "\nContatto: {nome}" + "\nDeal: {deal_name}"
  - DTSTART = scheduled_at in formato UTC
  - DTEND = scheduled_at + 30 minuti (default) o + 60 minuti per meeting

**AC-152.3 (Attivita senza orario)**: DATO che un'attivita pianificata ha solo data (no ora), ALLORA:
  - Il file .ics usa DTSTART come evento all-day (VALUE=DATE)
  - Non genera DTEND

**AC-152.4 (Generazione client-side)**: DATO che genero il file .ics, ALLORA:
  - La generazione avviene interamente nel browser (no API call)
  - Il download parte immediatamente senza round-trip server

**SP**: 3 | **Priorita**: Must Have | **Dipendenze**: US-151

---

## US-153: Collegamento Microsoft 365 Calendar (OAuth)

**Come** commerciale
**Voglio** collegare il mio account Microsoft 365 ad AgentFlow
**Per** far apparire automaticamente le attivita pianificate sul mio Outlook Calendar

**AC-153.1 (OAuth Flow)**: DATO che vado in Impostazioni > Calendario, QUANDO clicco "Collega Microsoft 365", ALLORA:
  - Vengo reindirizzato alla pagina di login Microsoft
  - Dopo il consenso, torno su AgentFlow con stato "Collegato" e badge verde
  - Il token viene salvato criptato nel DB (AES-256)

**AC-153.2 (Scope minimo)**: DATO che autorizzo AgentFlow, ALLORA:
  - L'app richiede solo `Calendars.ReadWrite` e `User.Read`
  - Non accede a email, file, contatti o altri dati Microsoft

**AC-153.3 (Token refresh)**: DATO che il token scade dopo 1 ora, QUANDO AgentFlow deve pushare un evento, ALLORA:
  - Il sistema usa il refresh token per ottenere un nuovo access token
  - Se il refresh fallisce (utente ha revocato), mostra "Calendario disconnesso — ricollegare"

**AC-153.4 (Disconnessione)**: DATO che clicco "Disconnetti Microsoft 365", ALLORA:
  - Il token viene rimosso dal DB
  - Le attivita future non vengono piu pushate
  - Gli eventi gia creati su Outlook restano (non vengono cancellati)

**SP**: 5 | **Priorita**: Must Have | **Dipendenze**: Nessuna

---

## US-154: Push attivita pianificate su Outlook Calendar

**Come** commerciale con Microsoft 365 collegato
**Voglio** che le attivita pianificate appaiano automaticamente sul mio Outlook Calendar
**Per** avere un'unica agenda senza dover copiare manualmente gli appuntamenti

**AC-154.1 (Push automatico)**: DATO che creo un'attivita con status="planned" e scheduled_at, QUANDO salvo, ALLORA:
  - Un evento viene creato su Outlook Calendar via Microsoft Graph API
  - L'evento contiene: subject, body (descrizione + contatto + deal), start/end, reminder 15min
  - L'`outlook_event_id` viene salvato sull'attivita per riferimento

**AC-154.2 (Update push)**: DATO che modifico data/ora di un'attivita pianificata, QUANDO salvo, ALLORA:
  - L'evento su Outlook viene aggiornato (PATCH via Graph API)
  - Se il push fallisce, l'attivita viene salvata comunque con warning "Sync Outlook fallita"

**AC-154.3 (Completamento)**: DATO che completo un'attivita, ALLORA:
  - L'evento su Outlook NON viene cancellato (resta come storico)
  - Opzionale: aggiungere "[Completata]" al titolo su Outlook

**AC-154.4 (Utente non collegato)**: DATO che NON ho collegato Microsoft 365, QUANDO creo un'attivita, ALLORA:
  - L'attivita viene creata normalmente senza push
  - Nessun errore o warning

**AC-154.5 (One-way only)**: DATO che il commerciale modifica l'evento su Outlook, ALLORA:
  - AgentFlow NON riceve la modifica (push one-way, no webhook)
  - L'attivita su AgentFlow resta invariata

**SP**: 5 | **Priorita**: Must Have | **Dipendenze**: US-153

---

## US-155: Link Calendly nel profilo commerciale

**Come** admin
**Voglio** configurare il link Calendly personale di ogni commerciale
**Per** permettere ai clienti di prenotare appuntamenti direttamente dalle email e dal deal detail

**AC-155.1 (Configurazione)**: DATO che vado in Impostazioni > Utenti > {commerciale}, ALLORA:
  - Vedo campo "Link Calendly" (URL, opzionale)
  - Al salvataggio, il valore viene salvato in `User.calendly_url`

**AC-155.2 (Bottone nel deal)**: DATO che il commerciale ha un link Calendly configurato, QUANDO apro un deal detail, ALLORA:
  - Appare bottone "Prenota appuntamento" che apre il link Calendly in nuova tab
  - Se il commerciale NON ha link Calendly, il bottone non appare

**AC-155.3 (Variabile email)**: DATO che creo un template email, ALLORA:
  - La variabile `{{calendly_link}}` e disponibile
  - Se l'utente ha Calendly configurato, viene sostituita col link
  - Se non configurato, la variabile viene rimossa (non mostra placeholder)

**AC-155.4 (Self-service)**: DATO che sono un commerciale (non admin), ALLORA:
  - Posso configurare il mio link Calendly dal mio profilo senza chiedere all'admin

**SP**: 3 | **Priorita**: Should Have | **Dipendenze**: Nessuna

---

## Riepilogo

| Story | Titolo | SP | Priorita | Effort |
|-------|--------|:--:|----------|--------|
| US-151 | Vista calendario FullCalendar | 5 | Must Have | 1.5 gg |
| US-152 | Export .ics client-side | 3 | Must Have | 0.5 gg |
| US-153 | OAuth Microsoft 365 | 5 | Must Have | 1 gg |
| US-154 | Push attivita → Outlook | 5 | Must Have | 0.5 gg |
| US-155 | Link Calendly profilo | 3 | Should Have | 0.5 gg |
| **TOTALE** | | **21 SP** | | **4 gg** |

**Nessuna nuova tabella DB.** Solo 3 campi su User: `microsoft_token` (JSON), `outlook_event_id` su CrmActivity (String), `calendly_url` (String).
