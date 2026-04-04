---
tipo: pattern
progetto: agentflow-pmi
data: 2026-04-03
stack: react, typescript, tailwind
confidenza: alta
tags: kanban, drag-drop, pipeline, crm, trello, frontend, react
---

# Pattern: Kanban drag-and-drop pipeline (stile Trello)

## Problema
I commerciali hanno bisogno di una vista visuale per gestire i deal: colonne = stadi pipeline, card = deal, drag-and-drop per spostare deal tra stadi.

## Soluzione architetturale

### Frontend
- Colonne orizzontali scrollabili, una per stage
- Card deal con: nome cliente, tipo deal, valore EUR, probabilita
- Drag-and-drop con `@dnd-kit/core` (React) o HTML5 DnD API
- Drop su colonna → PATCH /crm/deals/{id} con nuovo stage_id
- Totale per colonna (count + valore) nell'header
- Colori per probabilita o tipo deal
- Toggle tabella/Kanban per chi preferisce la lista

### Backend
- `GET /crm/deals` → lista deal con stage
- `PATCH /crm/deals/{id}` → aggiorna stage (+ probabilita automatica per stage)
- `GET /crm/pipeline/stages` → lista stadi con sequenza e probabilita default

### Librerie React consigliate
- `@dnd-kit/core` + `@dnd-kit/sortable` — leggero, accessibile, buona performance
- Alternative: `react-beautiful-dnd` (deprecato da Atlassian), `@hello-pangea/dnd` (fork mantenuto)

### Schema dati
```sql
crm_pipeline_stages (id, tenant_id, name, sequence, probability_default, color)
crm_deals (id, tenant_id, stage_id, contact_id, name, deal_type, expected_revenue, probability, ...)
```

## Anti-pattern
- NON caricare tutti i deal in memoria per grandi volumi — paginazione per stage
- NON aggiornare lo stage solo lato client — il PATCH deve andare al server con ottimistic UI
- NON dimenticare il mobile — su mobile il drag-and-drop non funziona bene, prevedere un select/dropdown
- NON usare react-beautiful-dnd (deprecato, non mantenuto)

## Applicazione in AgentFlow PMI
Vista Kanban per i 3 commerciali Nexa Data. ~100 deal/anno = ~20-30 deal attivi in pipeline contemporaneamente. Nessun problema di performance, tutto in memoria.
