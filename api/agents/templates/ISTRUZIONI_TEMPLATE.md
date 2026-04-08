# Template Offerta Nexa Data — Guida per Claude Cowork

## Come usare questo template

Carica `Template_Offerta_NexaData.docx` in Claude Cowork insieme a queste istruzioni.
Fornisci i dati dell'offerta e chiedi a Claude di compilare il template sostituendo i placeholder `{{...}}`.

Il template supporta sia offerte **a corpo (progetto)** sia offerte **Time & Material (T&M)**.

Claude deve fare unpack del docx, sostituire i placeholder nell'XML (attenzione: alcuni placeholder hanno le `{{` e `}}` in run XML separati dal nome — cercare e sostituire l'intero blocco di run), e rimpacchettare.

---

## Modalità di offerta supportate

### Offerta a corpo (progetto)
L'offerta prevede un impegno complessivo stimato in giorni/persona, con un importo totale fisso.
- `{{Descrizione_Offerta}}`: include scope, obiettivi, impegno stimato complessivo
- `{{Team_di_progetto}}`: ruoli con tariffe, giorni, importi
- `{{Stima_dettagliata_di_impegno}}`: breakdown per componente
- `{{PIANO_DI_SVILUPPO}}`: fasi con timeline
- `{{MODALITA_CONTRATTUALE}}`: specificare "Offerta a corpo" con importo totale, modalità di fatturazione (milestone o SAL), condizioni di pagamento

### Offerta Time & Material (T&M)
L'offerta prevede la messa a disposizione di risorse professionali con tariffe giornaliere, senza un impegno totale fisso.
- `{{Descrizione_Offerta}}`: descrivere il contesto, gli obiettivi e le attività previste senza impegno fisso
- `{{Team_di_progetto}}`: profili professionali con tariffe giornaliere (senza giorni totali)
- `{{Stima_dettagliata_di_impegno}}`: può essere omesso o usato per una stima indicativa non vincolante
- `{{PIANO_DI_SVILUPPO}}`: può descrivere le macro-attività previste senza vincolo di timeline
- `{{MODALITA_CONTRATTUALE}}`: specificare "Offerta Time & Material" con:
  - Tariffe giornaliere per profilo
  - Durata prevista dell'ingaggio (es. 6 mesi rinnovabili)
  - Impegno minimo/massimo mensile (se applicabile)
  - Fatturazione mensile a consuntivo su timesheet approvato
  - Preavviso di chiusura (es. 15 giorni lavorativi)
  - Eventuale cap massimo di spesa

---

## Esempio prompt — Offerta a corpo

```
Compila il template offerta Nexa Data (a corpo) con questi dati:

PROTOCOLLO: ND.ENG.2026.095
DATA_OFFERTA:       Roma 15/04/2026
NOME_CLIENTE: Acme Corporation S.p.A.
INDIRIZZO_CLIENTE: Via Roma 100
CAP_CITTA_CLIENTE: 20100,
PROVINCIA_CLIENTE: Milano (MI)
REFERENTE_CLIENTE: Dott. Marco Bianchi
TITOLO_OFFERTA: Piattaforma E-commerce B2B

TESTO_INTRODUTTIVO: In relazione ai colloqui intercorsi...

Descrizione_Offerta: Il progetto prevede lo sviluppo di una piattaforma e-commerce B2B...
Impegno complessivo stimato: 120 giorni/persona. Team: 2 risorse. Durata: circa 4 mesi.

MODALITA_CONTRATTUALE: Offerta a corpo per un importo complessivo di € 34.000,00 + IVA.
Fatturazione a milestone: 30% all'avvio, 40% al rilascio intermedio, 30% al collaudo.
Pagamento a 30 giorni data fattura.

[... resto dei campi]
```

## Esempio prompt — Offerta T&M

```
Compila il template offerta Nexa Data (Time & Material) con questi dati:

PROTOCOLLO: ND.ENG.2026.096
DATA_OFFERTA:       Roma 15/04/2026
NOME_CLIENTE: Beta Industries S.r.l.
INDIRIZZO_CLIENTE: Via Torino 50
CAP_CITTA_CLIENTE: 10100,
PROVINCIA_CLIENTE: Torino (TO)
REFERENTE_CLIENTE: Ing. Laura Verdi
TITOLO_OFFERTA: Supporto evolutivo piattaforma gestionale

TESTO_INTRODUTTIVO: In relazione ai colloqui intercorsi...

Descrizione_Offerta: Nexa Data mette a disposizione risorse professionali per attività
di sviluppo evolutivo e manutenzione della piattaforma gestionale del Cliente.
Le attività saranno pianificate di comune accordo su base mensile.

Team_di_progetto:
- Analista Tecnico Senior: € 300,00/giorno
- Sviluppatore Full Stack: € 250,00/giorno

Stima_dettagliata_di_impegno: Stima indicativa non vincolante: circa 20 giorni/mese
per un periodo iniziale di 6 mesi.

PIANO_DI_SVILUPPO: Le attività saranno pianificate in cicli mensili con priorità
concordate tramite backlog condiviso.

MODALITA_CONTRATTUALE: Offerta Time & Material.
Tariffe giornaliere:
- Analista Tecnico Senior: € 300,00/giorno
- Sviluppatore Full Stack: € 250,00/giorno
Durata: 6 mesi rinnovabili tacitamente.
Impegno indicativo: 15-25 giorni/mese complessivi.
Fatturazione: mensile a consuntivo su timesheet approvato dal Cliente entro il 5 del mese successivo.
Pagamento: 30 giorni data fattura.
Preavviso di chiusura: 15 giorni lavorativi.
Cap massimo mensile: da concordare.

ASSUNZIONE:
- Le attività saranno svolte da remoto salvo diverso accordo.
- Il Cliente fornirà accesso agli ambienti di sviluppo e test.
- Il timesheet sarà sottoposto ad approvazione mensile.
- Le tariffe sono valide per 12 mesi dalla data dell'offerta.

RISCHIO:
- Variabilità del carico di lavoro: gestita con flessibilità sull'impegno mensile.
- Turnover risorse: Nexa Data garantisce la sostituzione entro 10 giorni lavorativi.

[... riferimenti]
```

---

## Lista completa dei placeholder (31 unici, 32 occorrenze)

### Cover Page (9 placeholder)
| Placeholder | Descrizione | Esempio |
|---|---|---|
| `{{PROTOCOLLO}}` | Numero protocollo (compare 2 volte) | ND.ENG.2026.089 |
| `{{DATA_OFFERTA}}` | Spazi + città e data | `      Roma 01/04/2026` |
| `{{NOME_CLIENTE}}` | Ragione sociale | Engineering Ing. Informatica SpA |
| `{{INDIRIZZO_CLIENTE}}` | Indirizzo sede | P.le dell'Agricoltura, 24 |
| `{{CAP_CITTA_CLIENTE}}` | CAP con virgola | 00144, |
| `{{PROVINCIA_CLIENTE}}` | Città e provincia | Roma (RM) |
| `{{REFERENTE_CLIENTE}}` | Referente con titolo | Dott. Stefano Tomaselli |
| `{{TITOLO_OFFERTA}}` | Titolo del progetto | ENI – Applicativo Cessione del Credito |
| `{{TESTO_INTRODUTTIVO}}` | Paragrafo introduttivo | In relazione ai colloqui intercorsi... |

### Sez. 1 — Descrizione Offerta (5 placeholder)
| Placeholder | Descrizione |
|---|---|
| `{{Descrizione_Offerta}}` | Descrizione completa (scope, obiettivi, stima) |
| `{{TECNOLOGIE_INTRO}}` | Introduzione scelta tecnologica |
| `{{TECNOLOGIE_BACKEND}}` | Stack backend |
| `{{TECNOLOGIE_FRONTEND}}` | Stack frontend |
| `{{TECNOLOGIE_CONCLUSIONE}}` | Chiusura sezione tecnologie |

### Sez. 2 — Componenti del Sistema
| `{{Componenti_del_sistema}}` | Tutti i moduli/componenti |

### Sez. 3 — Team di Progetto
| `{{Team_di_progetto}}` | Ruoli, tariffe, giorni (corpo) o solo profili e tariffe (T&M) |

### Sez. 4 — Stima Dettagliata
| `{{Stima_dettagliata_di_impegno}}` | Breakdown per componente (corpo) o stima indicativa (T&M) |

### Sez. 5 — Piano di Sviluppo
| `{{PIANO_DI_SVILUPPO}}` | Fasi e timeline (corpo) o modalità di pianificazione (T&M) |

### Sez. 6 — Modalità Contrattuale e Quadro Economico *(NUOVA)*
| `{{MODALITA_CONTRATTUALE}}` | **A corpo**: importo totale, milestone, pagamento. **T&M**: tariffe, durata, fatturazione a consuntivo, cap, preavviso |

### Sez. 7 — Assunzioni e Dipendenze
| `{{ASSUNZIONE}}` | Vincoli e prerequisiti |

### Sez. 8 — Rischi Identificati
| `{{RISCHIO}}` | Rischi con impatto e mitigazione |

### Riferimenti (10 placeholder)
| Placeholder | Descrizione |
|---|---|
| `{{REF_COMMERCIALE_NOME}}` | Nome ref. commerciale |
| `{{REF_COMMERCIALE_EMAIL}}` | Email |
| `{{REF_COMMERCIALE_TEL}}` | Telefono |
| `{{REF_IT_NOME}}` | Nome ref. IT |
| `{{REF_IT_EMAIL}}` | Email |
| `{{REF_IT_TEL}}` | Telefono |
| `{{REF_AMM_NOME}}` | Nome ref. amministrativo |
| `{{REF_AMM_EMAIL}}` | Email |
| `{{REF_AMM_TEL}}` | Telefono |
| `{{FIRMATARIO}}` | Firmatario ordine |

---

## Nota tecnica per Claude Cowork

Alcuni placeholder inseriti manualmente in Word hanno le graffe `{{` e `}}` in **run XML separati** dal nome (es. `{{Descrizione_Offerta}}`, `{{PIANO_DI_SVILUPPO}}`). Quando si compila, sostituire tutti i run coinvolti con un singolo run contenente il testo finale.

## Struttura del documento
1. Cover page (grafica NEXA DATA, destinatario, titolo, firma)
2. Sommario (TOC)
3. Sez. 1 — Descrizione Offerta + Tecnologie
4. Sez. 2 — Componenti del sistema
5. Sez. 3 — Team di progetto
6. Sez. 4 — Stima dettagliata di impegno
7. Sez. 5 — Piano di sviluppo
8. Sez. 6 — Modalità contrattuale e quadro economico
9. Sez. 7 — Assunzioni e dipendenze
10. Sez. 8 — Rischi identificati
11. Riferimenti + firmatario
12. Clausola di riservatezza (testo standard)
