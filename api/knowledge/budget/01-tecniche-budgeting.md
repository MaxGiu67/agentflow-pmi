# Tecniche di Budgeting per PMI

## Quale tecnica usare

### 1. Incremental Budgeting (consigliato per aziende con storico)
- Si parte dai dati dell'anno precedente e si aggiusta
- Ideale per: aziende stabili, con 2+ anni di attivita
- Pro: semplice, veloce, realistico
- Contro: puo perpetuare inefficienze

**Quando l'agente lo usa**: il tenant ha almeno 1 anno di fatture importate.

```
Budget 2026 = Consuntivo 2025 × (1 + tasso crescita atteso)
```

### 2. Zero-Based Budgeting (consigliato per startup e nuove attivita)
- Si parte da zero: ogni voce va giustificata
- Ideale per: startup, nuove attivita, aziende in ristrutturazione
- Pro: elimina sprechi, forza la riflessione
- Contro: richiede piu tempo

**Quando l'agente lo usa**: il tenant e' nuovo, non ha storico, o ha dichiarato "startup" nell'onboarding.

```
Budget 2026 = domande all'utente su ogni voce
```

### 3. Activity-Based Budgeting (avanzato, per aziende di produzione)
- Si parte dalle attivita/commesse e si calcola il costo di ciascuna
- Ideale per: manifattura, costruzioni, servizi a progetto
- Pro: molto preciso, collega costi a output
- Contro: complesso, richiede dati dettagliati

**Quando l'agente lo usa**: ATECO manifattura (10-33) o costruzioni (41-43).

## Regola di scelta automatica

```python
def scegli_tecnica(tenant):
    if tenant.ha_storico_anno_precedente:
        if tenant.ateco_manifattura_o_costruzioni:
            return "activity_based"  # piu preciso per produzione
        return "incremental"         # piu semplice per servizi
    else:
        return "zero_based"          # startup, nessun riferimento
```

## Come si costruisce il budget (fasi)

1. **Budget delle vendite** — sempre il primo. Quanto fattureremo?
2. **Budget dei costi variabili** — proporzionali al fatturato (materie, provvigioni)
3. **Budget dei costi fissi** — indipendenti dal fatturato (affitto, personale, utenze)
4. **Budget degli investimenti** — CAPEX: acquisti beni strumentali
5. **Budget finanziario** — rate mutui, interessi
6. **Budget fiscale** — IRES, IRAP, IVA
7. **Sintesi** — Conto Economico Previsionale fino a EBITDA/EBIT/Utile Netto
