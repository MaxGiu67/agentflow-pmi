# Design: Puzzle Dashboard — Setup Aziendale

## Concept

La dashboard iniziale e' un **puzzle visivo**. Ogni pezzo rappresenta una fonte dati o funzione. Quando tutti i pezzi sono attivi, l'azienda e' "sotto controllo" e si sblocca la dashboard gestionale completa.

Il puzzle **sparisce** quando tutti i pezzi obbligatori sono attivi → l'utente vede la dashboard di consultazione (KPI, budget, cash flow).

## I 6 pezzi del puzzle

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│    │          │  │          │  │          │          │
│    │ FATTURE  │  │  BANCA   │  │  PAGHE   │          │
│    │          │  │          │  │          │          │
│    └──────────┘  └──────────┘  └──────────┘          │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│    │          │  │          │  │          │          │
│    │CORRISPET.│  │ BILANCIO │  │  BUDGET  │          │
│    │          │  │          │  │          │          │
│    └──────────┘  └──────────┘  └──────────┘          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## Dettaglio pezzi

| Pezzo | Cosa fa | Come si attiva | Cosa sblocca | Obbligatorio? |
|-------|---------|----------------|-------------|:---:|
| **Fatture** | Import fatture dal cassetto fiscale | SPID/CIE → sync cassetto | Fatturato, costi documentati, IVA | SI |
| **Banca** | Movimenti bancari | PDF/CSV/Open Banking | Cash Flow, Riconciliazione, Saldo | SI |
| **Paghe** | Costo del personale | PDF riepilogo paghe | Costo personale, margine reale | Se ha dipendenti |
| **Corrispettivi** | Incassi registratore | XML dal cassetto fiscale | Fatturato completo (retail) | Se ha RT |
| **Bilancio** | Saldi iniziali | PDF/CSV dal commercialista | Situazione patrimoniale | CONSIGLIATO |
| **Budget** | Piano economico | Conversazione con agente | Consuntivo, EBITDA, alert | SI |

## Dipendenze tra pezzi

```
Fatture ──→ Budget (serve per consuntivo ricavi/costi)
Paghe ────→ Budget (serve per consuntivo personale)
Banca ────→ Cash Flow (serve per previsione liquidita)
Fatture + Banca → Riconciliazione (match fatture ↔ movimenti)
Budget ───→ Dashboard gestionale (budget vs consuntivo)
```

Il **Budget** e' l'ultimo pezzo — si puo creare solo quando hai almeno Fatture importate (per il consuntivo). Se hai anche Paghe e Banca, il budget e' piu completo.

## Stati di ogni pezzo

| Stato | Icona | Colore | Significato |
|-------|-------|--------|-------------|
| **Bloccato** | 🔒 Lucchetto | Grigio | Non puo essere attivato (dipendenza mancante) |
| **Da configurare** | 🔓 Lucchetto aperto | Blu | Pronto per essere attivato |
| **Attivo** | ✅ Check | Verde | Funzionante, dati presenti |
| **Attenzione** | ⚠️ Warning | Arancione | Attivo ma con problemi (dati vecchi, errori) |

## Wizard per ogni pezzo

Cliccando su un pezzo "Da configurare", si apre un mini-wizard:

### Fatture (wizard SPID)
1. "Per importare le fatture serve l'accesso al cassetto fiscale"
2. "Accedi con SPID/CIE" → redirect
3. "Sync in corso..." → fatture importate
4. ✅ Pezzo attivo

### Banca (wizard import)
1. "Come vuoi collegare la banca?"
2. Opzioni: PDF estratto conto / CSV / Open Banking
3. Upload/Connect → movimenti importati
4. ✅ Pezzo attivo

### Paghe (wizard upload)
1. "Carica il PDF del riepilogo paghe dal consulente"
2. Upload → parsing → preview
3. Conferma → ✅ Pezzo attivo

### Corrispettivi (auto dal cassetto)
1. Se il cassetto fiscale ha corrispettivi → si attiva automaticamente
2. Altrimenti: "Non hai un registratore telematico? Salta questo pezzo"

### Bilancio (wizard import)
1. "Per partire con i saldi corretti, carica il bilancio"
2. Upload PDF/CSV → parsing → preview → conferma
3. ✅ Pezzo attivo (o "Salta — procedi senza storico")

### Budget (conversazione agente)
1. "Creiamo il budget 2026 insieme"
2. Domande guidate per settore (da knowledge base)
3. CE previsionale → conferma
4. ✅ Pezzo attivo → si sblocca la dashboard gestionale

## Transizione Puzzle → Dashboard

Quando i pezzi OBBLIGATORI sono tutti attivi (Fatture + Banca + Budget + eventualmente Paghe):

```
Puzzle si dissolve → appare la Dashboard Gestionale
  - Home conversazionale
  - Budget vs Consuntivo
  - Cash Flow
  - KPI
  - Alert
```

Il puzzle resta accessibile da Impostazioni → "Setup Azienda" per aggiungere pezzi mancanti o riconfigurare.
