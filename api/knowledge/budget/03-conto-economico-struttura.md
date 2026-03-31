# Struttura Conto Economico Previsionale — Da domande semplici a EBITDA

## Schema Conto Economico Civilistico (art. 2425 CC) semplificato

```
A) VALORE DELLA PRODUZIONE
   A1. Ricavi vendite e prestazioni
   A5. Altri ricavi (contributi, affitti attivi, plusvalenze)
   ───────────────────────────────────
   TOTALE RICAVI (A)

B) COSTI DELLA PRODUZIONE
   B6.  Materie prime, sussidiarie, merci
   B7.  Servizi (consulenze, utenze, manutenzioni, trasporti)
   B8.  Godimento beni terzi (affitti, leasing, noleggi)
   B9.  Costo del personale
        B9a. Salari e stipendi
        B9b. Oneri sociali (INPS c/azienda, INAIL)
        B9c. TFR (accantonamento)
        B9d. Altri costi personale
   B10. Ammortamenti e svalutazioni
        B10a. Ammortamento immobilizzazioni immateriali
        B10b. Ammortamento immobilizzazioni materiali
   B11. Variazione rimanenze materie
   B12. Accantonamenti per rischi
   B13. Altri accantonamenti
   B14. Oneri diversi di gestione (tasse, contributi, sanzioni)
   ───────────────────────────────────
   TOTALE COSTI (B)

   ═══════════════════════════════════
   EBITDA = TOTALE RICAVI - TOTALE COSTI + Ammortamenti (B10)
   (Margine Operativo Lordo — prima di ammortamenti)

   EBIT = TOTALE RICAVI - TOTALE COSTI
   (Risultato Operativo — dopo ammortamenti)
   ═══════════════════════════════════

C) PROVENTI E ONERI FINANZIARI
   C16. Interessi attivi e proventi finanziari
   C17. Interessi passivi e oneri finanziari (mutui, fidi, leasing)
   ───────────────────────────────────
   TOTALE (C)

D) RETTIFICHE DI VALORE ATTIVITA FINANZIARIE
   (raro per PMI, solitamente zero)

   ═══════════════════════════════════
   EBT = EBIT + C + D
   (Risultato prima delle imposte)
   ═══════════════════════════════════

   IMPOSTE
   - IRES: 24% sull'utile ante imposte
   - IRAP: ~3.9% sul valore della produzione (A - B + B9)
   ───────────────────────────────────

   ═══════════════════════════════════
   UTILE (PERDITA) NETTO
   ═══════════════════════════════════
```

## Mappatura: Domande imprenditore → Voce CE

| Domanda dell'agente | Voce CE | Codice |
|---------------------|---------|--------|
| "Quanto fatturerai?" | Ricavi vendite | A1 |
| "Altri ricavi (affitti, contributi)?" | Altri ricavi | A5 |
| "Quanto spendi in materie prime/merci?" | Materie prime | B6 |
| "Costo fornitori/consulenze?" | Servizi | B7 |
| "Affitto/leasing mensile?" | Godimento beni terzi | B8 |
| "Quanti dipendenti? RAL media?" | Costo personale | B9 (calcolo auto) |
| "Acquisti beni strumentali?" | Ammortamenti | B10 (calcolo auto) |
| "Utenze mensili?" | Oneri diversi | B14 |
| "Rate mutuo/finanziamento?" | Oneri finanziari | C17 |

## Calcoli automatici dell'agente

### Da RAL a costo azienda completo
```
Input: num_dipendenti, RAL_media
  Salari lordi = RAL × num_dipendenti                    (B9a)
  Contributi INPS c/azienda = Salari × 30%               (B9b)
  INAIL = Salari × 0.4-1.5% (dipende dal settore)        (B9b)
  TFR = Salari × 6.91%                                   (B9c)
  Costo totale = Salari + INPS + INAIL + TFR
```

### Da acquisto bene a ammortamento
```
Input: importo_acquisto, tipo_bene
  Aliquota = tabella ministeriale (20% HW, 25% auto, 12% mobili...)
  Ammortamento annuo = importo × aliquota
  Primo anno = 50% dell'ammortamento annuo (regola fiscale)
```

### Calcolo imposte
```
IRES = max(0, EBT) × 24%
IRAP = max(0, Valore_Produzione) × 3.9%
  dove Valore_Produzione = A - B + B9 (costo lavoro non deducibile IRAP)
```

### EBITDA %
```
EBITDA % = EBITDA / Ricavi × 100
Benchmark: confronta con tabella settore (02-benchmark-settore.md)
```

## Distribuzione mensile del budget

Non tutte le voci sono distribuite uniformemente:

| Voce | Distribuzione mensile |
|------|----------------------|
| Ricavi | Variabile per settore (ristorazione: stagionale, IT: uniforme) |
| Personale | Uniforme × 13-14 mensilita (13a a Dicembre, 14a a Giugno/Luglio) |
| Affitto | Uniforme × 12 |
| Utenze | Variabile (riscaldamento inverno, climatizzazione estate) |
| Ammortamenti | Uniforme × 12 |
| IRES/IRAP | Acconti: Giugno (40%) + Novembre (60%), Saldo: Giugno |
| IVA | Trimestrale (16 maggio, 16 agosto, 16 novembre, 16 marzo) |
| INPS | Mensile (16 del mese successivo) |
