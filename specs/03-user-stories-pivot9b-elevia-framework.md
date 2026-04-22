# User Stories — Pivot 9b: Framework CRM ElevIA

**AgentFlow PMI — Integrazione playbook commerciale ElevIA**

**Data:** 9 aprile 2026
**Prerequisito:** Pivot 9 completato (pipeline templates, Sales Agent, Elevia Engine)
**Principio:** AgentFlow orchestra, Brevo esegue. L'agente suggerisce, l'umano approva.

---

## Overview

Il Pivot 9b traduce il Framework CRM ElevIA (documento `CRM_Arc_P2C_v126_ElevIA.md`) in regole operative dentro AgentFlow. Copre 7 gap rispetto al Pivot 9:

1. Sistema tag awareness (1-5) + tag LM + tag funnel + tag evento
2. Seed 9 sequenze email ElevIA in Brevo con routing awareness-driven
3. Regola "una sola sequenza attiva per prospect" + stop su risposta
4. Lead Magnet come entita CRM con tracking download
5. Eventi INTRO/INSIGHT con iscritti, no-show e sequenze pre/post
6. Orchestrazione Brevo da AgentFlow (trigger/pause/abort sequenze)
7. KPI funnel ElevIA (awareness distribution, conversion rate, LM performance)

**Epic:** 2 (EPIC 23: ElevIA Awareness Engine, EPIC 24: ElevIA Sequence Orchestration)
**Stories:** 7 (US-222 → US-228)
**SP stimati:** ~45
**Sprint:** 46-47 (~4 settimane, dopo Pivot 9 e Pivot 10)

---

## EPIC 23: ElevIA Awareness Engine

### US-222: Sistema tag contatto multi-dimensione

**Come** sistema
**Voglio** che ogni contatto CRM abbia tag strutturati su 4 dimensioni indipendenti (awareness, LM, funnel, evento)
**Per** implementare il routing del framework ElevIA basato sullo stato del prospect

**AC-222.1 (Modello CrmContactTag)**: DATO che il sistema si avvia, ALLORA:
  - Esiste la tabella `crm_contact_tags`: id, tenant_id, contact_id, tag_category (awareness/lm/funnel/evento/sequenza), tag_key, tag_value, applied_at, removed_at (nullable), applied_by (user_id o "system"), reason_code
  - Index composto su (tenant_id, contact_id, tag_category, tag_key)

**AC-222.2 (Awareness 1-5)**: DATO che creo un contatto con origine `linkedin_dm`, ALLORA:
  - Il sistema assegna automaticamente tag: category=awareness, key=level, value=1
  - Nella scheda contatto vedo badge "Aw1 — Unaware"
  - I 5 livelli sono: 1=Unaware, 2=Problem Aware, 3=Solution Aware, 4=Product Aware, 5=Most Aware

**AC-222.3 (Tag LM cumulativi)**: DATO che il prospect scarica l'Ebook "AI per PMI", ALLORA:
  - Il sistema aggiunge tag: category=lm, key=LM_EB_AI-PMI, value=downloaded, applied_at=now
  - Se scarica un secondo LM, il tag si AGGIUNGE (non sovrascrive)
  - Nella scheda contatto vedo tutti i tag LM accumulati

**AC-222.4 (Tag Funnel)**: DATO che un contatto viene acquisito, ALLORA:
  - Tag automatico: category=funnel, key=CM (Community Member)
  - Transizioni possibili: CM → LTN (30gg senza engagement) → Offerta_Chiesta → Ordine_Firmato
  - Ogni transizione registra applied_at + reason_code

**AC-222.5 (Tag Evento)**: DATO che un contatto viene invitato a INTRO Go, ALLORA:
  - Tag: category=evento, key=INTRO_Go_invitato, value=data_evento
  - Post-partecipazione: key=INTRO_Go_partecipato → awareness sale a 4 (manuale obbligatorio)

**AC-222.6 (Tag Sequenza)**: DATO che un contatto entra nella sequenza Welcome, ALLORA:
  - Tag: category=sequenza, key=Welcome_Started, applied_at=now
  - Al completamento: key=Welcome_Finished

**AC-222.7 (Audit trail)**: DATO che l'awareness cambia da 2 a 4, ALLORA:
  - Il vecchio tag ha removed_at valorizzato
  - Il nuovo tag ha applied_at + applied_by + reason_code="INTRO_Go_partecipato"
  - L'audit log mostra: "2→4 il 15/04 da Pietro (INTRO Go partecipato)"

**AC-222.8 (API)**: DATO che chiamo GET /crm/contacts/{id}/tags, ALLORA:
  - Risposta raggruppata per category: {awareness: [...], lm: [...], funnel: [...], evento: [...], sequenza: [...]}
  - Supporto filtro per category e tag_key

**AC-222.9 (Regola fondamentale)**: DATO che un contatto scarica un Lead Magnet, ALLORA:
  - Il tag LM si aggiunge (LM_EB_NomeSpecifico)
  - Il tag awareness NON cambia — l'awareness si aggiorna SOLO con engagement reale (email open/click) o partecipazione eventi (manuale)

**SP**: 8 | **Priorita**: Must Have | **Epic**: ElevIA Awareness Engine | **Dipendenze**: Nessuna

---

### US-223: Lead Magnet come entita CRM

**Come** admin
**Voglio** gestire i Lead Magnet con tipo, nome, LP URL e sequenza email associata
**Per** tracciare quale LM ha catturato ogni prospect e attivare la sequenza corretta

**AC-223.1 (Modello)**: DATO che il sistema si avvia, ALLORA:
  - Tabella `crm_lead_magnets`: id, tenant_id, code (LM_EB_AI-PMI), name, format (ebook/personal_video/eec/microcourse/chatbot), description, landing_page_url, thank_you_page_url, welcome_sequence_id (FK opzionale), is_active
  - Seed con almeno 1 LM: Ebook "AI per PMI" (il formato gia prodotto)

**AC-223.2 (Tracking download)**: DATO che un prospect compila il form sulla LP dell'Ebook, QUANDO il webhook arriva (Brevo o form custom), ALLORA:
  - Il sistema crea/aggiorna CrmContact (se non esiste)
  - Assegna tag: category=lm, key=LM_EB_AI-PMI
  - Assegna tag: category=funnel, key=CM (Community Member)
  - Avvia la sequenza Welcome (se non gia attiva) — W1 entro 2 minuti
  - NON aggiorna awareness (resta a 1 se era 1)

**AC-223.3 (Multi-download)**: DATO che il prospect scarica un secondo LM (Microcorso Legacy), ALLORA:
  - Nuovo tag LM si aggiunge: LM_MC_Legacy
  - Se la sequenza Welcome e gia completata, nessuna nuova sequenza parte
  - Se e in corso, continua normalmente

**AC-223.4 (CRUD)**: DATO che l'admin va in Impostazioni > Lead Magnet, ALLORA:
  - CRUD completo: lista, crea, modifica, disattiva
  - Ogni LM mostra: quanti download, quanti hanno raggiunto awareness 2+

**SP**: 5 | **Priorita**: Must Have | **Epic**: ElevIA Awareness Engine | **Dipendenze**: US-222

---

### US-224: Eventi INTRO e INSIGHT

**Come** commerciale/fractional
**Voglio** gestire eventi INTRO e INSIGHT con iscritti, calendario, no-show tracking e sequenze pre/post
**Per** far progredire i prospect nell'awareness (3→4 con INTRO, 4→5 con INSIGHT)

**AC-224.1 (Modello CrmEvent)**: DATO che creo un evento INTRO Go, ALLORA:
  - Tabella `crm_events`: id, tenant_id, event_type (intro/insight), service_code (Go), title, date, location_type (online/in_person), location_detail (link o indirizzo), capacity, description, is_active
  - L'evento appare nel calendario (FullCalendar integration)

**AC-224.2 (Iscrizione)**: DATO che invito un prospect all'evento INTRO Go, ALLORA:
  - Tabella `crm_event_attendees`: id, event_id, contact_id, status (invited/registered/attended/no_show), invited_at, registered_at, attended_at
  - Tag evento assegnato: INTRO_Go_invitato
  - Sequenza INTRO_Calendar attivata (3 email pre-evento: -3gg, -1gg, -1h)

**AC-224.3 (Partecipazione confermata)**: DATO che post-evento marco il prospect come "partecipato", ALLORA:
  - Status → attended
  - Tag: INTRO_Go_partecipato
  - Awareness → 4 (aggiornamento con reason_code="INTRO_Go_partecipato", applied_by=user)
  - Sequenza INTRO_Followup attivata (3 email: +1gg, +4gg, +9gg)

**AC-224.4 (No-show)**: DATO che il prospect non partecipa, ALLORA:
  - Status → no_show
  - Awareness NON avanza
  - INTRO_Followup NON si avvia
  - Il commerciale decide se re-invitare al prossimo INTRO

**AC-224.5 (INSIGHT)**: DATO che creo un evento INSIGHT Go e marco partecipazione, ALLORA:
  - Stessa logica di INTRO ma: awareness → 5
  - Sequenza INSIGHT_Followup (4 email: +1gg, +4gg, +9gg, +17gg)
  - Awareness 5 = da qui in poi gestione manuale, nessuna sequenza educativa

**AC-224.6 (Vista eventi)**: DATO che accedo a Commerciale > Eventi, ALLORA:
  - Lista eventi con: tipo, data, iscritti/capacita, partecipanti confermati
  - Dettaglio evento con lista iscritti + status + azioni bulk (segna tutti come partecipato)

**SP**: 8 | **Priorita**: Must Have | **Epic**: ElevIA Awareness Engine | **Dipendenze**: US-222

---

### US-225: KPI Funnel ElevIA

**Come** manager/commerciale
**Voglio** vedere i KPI specifici del funnel ElevIA (distribuzione awareness, conversioni, LM performance)
**Per** capire dove il funnel si blocca e ottimizzare le azioni commerciali

**AC-225.1 (Distribuzione awareness)**: DATO che ho 200 contatti con awareness taggata, ALLORA:
  - Widget: "Awareness 1: 120 (60%), Aw2: 45 (22.5%), Aw3: 20 (10%), Aw4: 10 (5%), Aw5: 5 (2.5%)"
  - Visualizzazione a imbuto o barre

**AC-225.2 (Tassi conversione)**: DATO che calcolo le conversioni, ALLORA:
  - Aw3 → INTRO partecipato: X%
  - INTRO → INSIGHT partecipato: Y%
  - INSIGHT → Offerta_Chiesta: Z%
  - Offerta_Chiesta → Ordine_Firmato: W%
  - Ogni tasso calcolato sui tag presenti

**AC-225.3 (LM piu performante)**: DATO che ho 3 Lead Magnet attivi, ALLORA:
  - Per ogni LM: download totali, % che raggiunge awareness 2+, % che raggiunge awareness 3+
  - Ordinato per conversion rate (non per volume)

**AC-225.4 (Contatti in LTN)**: DATO che voglio vedere i prospect "dormienti", ALLORA:
  - Conteggio contatti con tag funnel=LTN attivo
  - Data media di ingresso in LTN
  - Quanti "risvegliati" (tag ltn_risvegliato) nell'ultimo trimestre

**AC-225.5 (Ciclo commerciale medio)**: DATO che ho deal Elevia chiusi, ALLORA:
  - Giorni medi da tag CM (primo contatto) a Ordine_Firmato
  - Breakdown: CM→Aw3 (Xgg), Aw3→INTRO (Ygg), INTRO→INSIGHT (Zgg), INSIGHT→Ordine (Wgg)

**AC-225.6 (Endpoint API)**: DATO che chiamo GET /elevia/analytics/funnel, ALLORA:
  - Ritorna tutti i KPI sopra in un unico payload, filtrabile per periodo

**SP**: 5 | **Priorita**: Should Have | **Epic**: ElevIA Awareness Engine | **Dipendenze**: US-222, US-223, US-224

---

## EPIC 24: ElevIA Sequence Orchestration

### US-226: Seed 9 sequenze ElevIA in Brevo

**Come** sistema
**Voglio** che le 9 sequenze email del framework ElevIA siano create come template in Brevo con timing e condizioni corrette
**Per** avere il playbook commerciale pronto all'uso dal giorno 1

**AC-226.1 (Welcome — 3 email)**: DATO che il sistema viene configurato, ALLORA:
  - Sequenza "ElevIA Welcome" creata in Brevo (o nel DB sequenze interno):
    - W1: immediata (entro 2 min) — consegna materiale + presentazione mittente
    - W2: +2 giorni — insight derivato dal materiale
    - W3: +5 giorni — anticipazione Educational + invito LinkedIn
  - Trigger: tag CM assegnato (download LM o iscrizione)

**AC-226.2 (Educational — 5 email)**: DATO che il prospect completa Welcome con engagement (2+ open o 1 click), ALLORA:
  - Sequenza "ElevIA Educational" si attiva:
    - E1: +3gg da W3 — dati di mercato e casi
    - E2: +7gg da E1 — opzioni del mercato
    - E3: +7gg da E2 — criteri di valutazione + link contenuto
    - E4: +7gg da E3 — caso reale
    - E5: +7gg da E4 — invito soft a INTRO con CTA → LP
  - Se dopo E5 nessuna prenotazione INTRO entro 14gg → entra in LTN

**AC-226.3 (LTN — 13 email settimanali)**: DATO che il prospect non procede dopo Educational o Welcome senza engagement, ALLORA:
  - Sequenza "ElevIA LTN" ciclica:
    - Sett 1-4: trend e problemi del settore (Aw target 2)
    - Sett 5-8: approcci comparati (Aw target 3)
    - Sett 9-11: soluzione concreta (Aw target 3+)
    - Sett 12: social proof
    - Sett 13: re-invito INTRO con CTA → LP
  - Click sett 5-11 → tag ltn_risvegliato + awareness → 3 + rientra in Educational da E3
  - Fine ciclo senza segnale → pausa 90gg → nuovo ciclo

**AC-226.4 (INTRO — 3 sotto-sequenze)**: DATO che il prospect viene invitato a INTRO, ALLORA:
  - INTRO_Invita (3 email): invio, +3gg reminder, +5gg urgency
  - INTRO_Calendar (3 email): -3gg conferma, -1gg anticipazione, -1h reminder
  - INTRO_Followup (3 email): +1gg riepilogo, +4gg FAQ, +9gg invito INSIGHT
  - Trigger: tag INTRO_Go_invitato (Invita), INTRO_Go_registrato (Calendar), INTRO_Go_partecipato (Followup)

**AC-226.5 (INSIGHT — 3 sotto-sequenze)**: DATO che il prospect con INTRO partecipato viene invitato a INSIGHT, ALLORA:
  - INSIGHT_Invita (3 email): caso reale, +3gg risultato, +5gg urgency
  - INSIGHT_Calendar (3 email): -3gg conferma, -1gg preparazione decisionale, -1h reminder
  - INSIGHT_Followup (4 email): +1gg riepilogo offerta, +4gg obiezioni, +9gg urgency, +17gg "se non e il momento"
  - Dopo I2_F4 senza risposta → lista manuale commerciale (NON LTN — awareness 5 e decisione)

**AC-226.6 (Template email)**: DATO che creo le sequenze, ALLORA:
  - Ogni email ha: subject, body con variabili {{nome}}, {{azienda}}, {{settore}}, CTA con link LP
  - I contenuti sono placeholder editabili dall'admin
  - Tag sequenza (Welcome_Started/Finished etc.) si aggiornano automaticamente

**SP**: 8 | **Priorita**: Must Have | **Epic**: ElevIA Sequence Orchestration | **Dipendenze**: US-222, US-223

---

### US-227: Orchestratore sequenze awareness-driven

**Come** sistema
**Voglio** che AgentFlow gestisca il routing tra sequenze basandosi su awareness, engagement e regole del framework
**Per** far funzionare il funnel ElevIA in automatico senza intervento manuale

**AC-227.1 (Una sola sequenza attiva)**: DATO che un prospect e nella sequenza Educational, QUANDO viene invitato a INTRO, ALLORA:
  - La sequenza Educational viene PAUSATA (non eliminata)
  - La sequenza INTRO_Invita si attiva
  - Campo `active_sequence_id` su CrmContact aggiornato
  - Se il prospect non registra per INTRO dopo le 3 email → rientra in Educational dal punto in cui era

**AC-227.2 (Stop su risposta)**: DATO che un prospect risponde a un'email della sequenza (reply rilevato da Brevo webhook), ALLORA:
  - La sequenza attiva viene PAUSATA immediatamente
  - Tag: "manual_takeover" + timestamp
  - Il commerciale riceve notifica (in-app + opzionale Slack)
  - La sequenza riprende SOLO su decisione esplicita del commerciale

**AC-227.3 (Routing Welcome → Educational)**: DATO che W3 e stata inviata, ALLORA:
  - Se engagement (2+ open O 1 click nella sequenza Welcome): attiva Educational
  - Se nessun engagement dopo 30gg: attiva LTN
  - Se reply: stop + gestione manuale

**AC-227.4 (Routing Educational → INTRO/LTN)**: DATO che E5 e stata inviata, ALLORA:
  - Se prenotazione INTRO entro 14gg: attiva INTRO_Invita
  - Se nessuna prenotazione dopo 14gg: attiva LTN
  - Se reply: stop + gestione manuale

**AC-227.5 (Awareness 5 = manuale)**: DATO che un prospect raggiunge awareness 5 (INSIGHT partecipato), ALLORA:
  - Nessuna sequenza educativa viene attivata
  - Solo INSIGHT_Followup (4 email decision-oriented)
  - Dopo I2_F4 senza risposta: lista manuale del commerciale
  - Il sistema NON manda il prospect in LTN

**AC-227.6 (Abort on manual outreach)**: DATO che il commerciale crea un'attivita manuale (call, email diretta, meeting) sul contatto, ALLORA:
  - La sequenza attiva viene pausata per 7 giorni
  - Dopo 7gg senza nuova attivita manuale: la sequenza riprende automaticamente
  - Se nuova attivita manuale entro 7gg: pausa si rinnova

**AC-227.7 (Risveglio da LTN)**: DATO che un prospect in LTN clicca un link nelle settimane 5-11, ALLORA:
  - Tag: ltn_risvegliato
  - Awareness → 3
  - LTN si pausa
  - Rientra in Educational da E3
  - Notifica al commerciale: "[Nome] si e risvegliato dalla LTN. Awareness aggiornata a 3."

**SP**: 8 | **Priorita**: Must Have | **Epic**: ElevIA Sequence Orchestration | **Dipendenze**: US-222, US-226

---

### US-228: Tool Sales Agent per framework ElevIA

**Come** commerciale/fractional
**Voglio** che il Sales Agent abbia tool specifici per gestire awareness, sequenze e eventi del framework ElevIA
**Per** governare il funnel direttamente dalla chat senza andare in 5 pagine diverse

**AC-228.1 (Tool: update_awareness)**: DATO che chiedo "aggiorna awareness di Mario Rossi a 4", ALLORA:
  - L'agente chiede conferma: "Confermi awareness → 4 (Product Aware) per Mario Rossi? Motivo?"
  - Se confermo con motivo ("ha partecipato a INTRO Go"): aggiorna tag + audit trail
  - Se il salto e > 2 livelli: warning "Salto da 1 a 4 — sei sicuro? Normalmente il percorso e 1→2→3→4."

**AC-228.2 (Tool: suggest_sequence)**: DATO che chiedo "cosa devo fare con questo prospect?", ALLORA:
  - L'agente valuta: awareness attuale, tag funnel, sequenza attiva, ultimo engagement
  - Suggerisce: "Mario Rossi e awareness 3, ha completato Educational. Suggerisco di invitarlo a INTRO Go (prossimo evento: 25/04). Vuoi che attivi INTRO_Invita?"
  - Se confermo: attiva la sequenza (con le regole di US-227)

**AC-228.3 (Tool: event_invite)**: DATO che chiedo "invita questo prospect all'INTRO del 25/04", ALLORA:
  - L'agente: crea record in crm_event_attendees, assegna tag INTRO_Go_invitato, attiva sequenza INTRO_Invita
  - "Fatto. Ho invitato Mario Rossi all'INTRO Go del 25/04. Sequenza INTRO_Invita attivata (3 email)."

**AC-228.4 (Tool: mark_attendance)**: DATO che dopo l'evento chiedo "segna partecipati i seguenti: Mario Rossi, Anna Verdi", ALLORA:
  - L'agente aggiorna in bulk: status=attended, tag INTRO_Go_partecipato, awareness → 4
  - Attiva INTRO_Followup per ciascuno
  - "Aggiornati 2 partecipanti. Awareness → 4. INTRO_Followup attivata per entrambi."

**AC-228.5 (Tool: funnel_status)**: DATO che chiedo "com'e il funnel Elevia?", ALLORA:
  - L'agente mostra: distribuzione awareness (1-5), contatti in LTN, prossimo evento, conversion rate
  - "Funnel Elevia: 120 Aw1, 45 Aw2, 20 Aw3, 10 Aw4, 5 Aw5. 32 in LTN. Prossimo INTRO: 25/04 (8 iscritti). Conversion Aw3→INTRO: 50%."

**SP**: 5 | **Priorita**: Must Have | **Epic**: ElevIA Sequence Orchestration | **Dipendenze**: US-222, US-224, US-226, US-227

---

## Riepilogo

| Story | Titolo | SP | Epic | Prio |
|-------|--------|:--:|------|------|
| US-222 | Sistema tag contatto multi-dimensione | 8 | 23 | Must |
| US-223 | Lead Magnet come entita CRM | 5 | 23 | Must |
| US-224 | Eventi INTRO e INSIGHT | 8 | 23 | Must |
| US-225 | KPI Funnel ElevIA | 5 | 23 | Should |
| US-226 | Seed 9 sequenze ElevIA in Brevo | 8 | 24 | Must |
| US-227 | Orchestratore sequenze awareness-driven | 8 | 24 | Must |
| US-228 | Tool Sales Agent per framework ElevIA | 5 | 24 | Must |

**Totale: 7 stories, 47 SP, 2 Epic**
**Sprint stimati: 46-47 (~4 settimane)**
**Dipendenza: Pivot 9 completato (pipeline templates + Sales Agent + Elevia Engine)**

---

*Pivot 9b — Framework CRM ElevIA — 9 aprile 2026*
*Prossimo passo: sprint plan con task breakdown*
