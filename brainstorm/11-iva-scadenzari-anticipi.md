# IVA, Scadenzari, Cash Flow, Anticipi Fatture — Spec

## Priorita di implementazione
1. Fix IVA — ricavi/costi al netto in Dashboard e Budget
2. Scadenzario attivo/passivo — da fatture con data scadenza
3. Cash flow previsionale — da scadenzario + saldo banca
4. Anticipo fatture — fidi bancari con confronto costi per banca

---

## 1. Fix IVA

Dashboard e Budget devono usare `importo_netto` (non `importo_totale`).
L'IVA non e un ricavo ne un costo — e un transito verso lo Stato.

```
Fattura attiva 1.220€ → Ricavo: 1.000€ | IVA debito: 220€
Fattura passiva 610€  → Costo: 500€    | IVA credito: 110€
IVA netta = 220 - 110 = 110€ da versare
```

File da modificare:
- api/modules/dashboard/service.py — usare importo_netto
- api/modules/ceo/service.py — idem
- api/modules/controller/service.py — _get_yearly_actuals, _get_monthly_actuals

---

## 2. Scadenzario Attivo e Passivo

### Scadenzario Attivo (crediti da incassare)
- Fonte: fatture attive con data_scadenza (data_fattura + giorni_pagamento)
- Stato: da_incassare | parziale | incassato | insoluto
- Match con movimenti banca per chiusura automatica

### Scadenzario Passivo (debiti da pagare)
- Fonte: fatture passive + stipendi + rate mutui + F24 + affitti
- Stato: da_pagare | pagato | scaduto

### Modello dati
```
Scadenza
  id, tenant_id
  tipo: "attivo" | "passivo"
  source_type: "fattura" | "stipendio" | "f24" | "mutuo" | "contratto"
  source_id: UUID (FK alla fattura/mutuo/contratto)
  controparte: "Cliente A" / "Fornitore X"
  importo_lordo: 1.220€
  importo_netto: 1.000€
  importo_iva: 220€
  data_scadenza: date
  data_pagamento: date | null
  stato: "aperto" | "pagato" | "insoluto" | "parziale"
  banca_appoggio: UUID (FK → BankAccount) — IBAN fattura
  anticipata: bool
  anticipo_id: UUID | null (FK → InvoiceAdvance)
```

---

## 3. Cash Flow Previsionale

```
Saldo banca oggi:           50.000€
+ Incassi previsti 30gg:    +3.660€  (scadenzario attivo)
- Pagamenti previsti 30gg: -15.720€  (scadenzario passivo)
= Saldo previsto 30gg:     37.940€
```

Vista: grafico a cascata (waterfall) con barre giornaliere/settimanali.

---

## 4. Anticipo Fatture

### Configurazione per banca (BankFacility)
```
BankFacility
  id, tenant_id
  bank_account_id: FK → BankAccount
  tipo: "anticipo_fatture" | "sbf" | "riba"
  plafond: 200.000€
  percentuale_anticipo: 80%
  tasso_interesse_annuo: 4.5%
  commissione_presentazione_pct: 0.3%
  commissione_incasso: 2€
  commissione_insoluto: 15€
  giorni_max: 120
```

### Singolo anticipo (InvoiceAdvance)
```
InvoiceAdvance
  id, tenant_id
  facility_id: FK → BankFacility
  invoice_id: FK → Invoice (attiva)
  importo_fattura: 10.000€
  importo_anticipato: 8.000€
  commissione: 30€
  interessi_stimati: 88,77€
  interessi_effettivi: null (calcolato a chiusura)
  data_presentazione: date
  data_scadenza_prevista: date
  data_chiusura: date | null
  stato: "attivo" | "incassato" | "insoluto"
```

### Flusso
1. Fattura creata → banca di appoggio (IBAN) definita
2. Imprenditore sceglie di anticipare → sceglie fido bancario (puo essere banca diversa)
3. Sistema calcola costo anticipo e confronta tra banche disponibili
4. Conferma → anticipo attivo → cash flow aggiornato
5. Alla scadenza: incasso → chiude anticipo + fattura, oppure insoluto → riaddebito

### Confronto banche
Il sistema confronta il costo dell'anticipo su ogni fido disponibile:
- Anticipo netto, commissioni, interessi stimati, costo totale, costo % annuo
- Consiglia la banca piu conveniente

---

## Note
- Banca di appoggio (IBAN fattura) ≠ Banca anticipo (fido)
- L'IVA va sempre scorporata nei KPI (ricavi/costi al netto)
- Gli interessi e commissioni anticipo vanno in budget come "oneri_finanziari" / "costi_bancari"
