# Tech Spec — Agentic Dashboard

**Data:** 2026-03-25

---

## Architettura

```
┌─────────────────────────────────────────────────────────┐
│                    Dashboard Page                         │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Year Selector [2024 ▼]                           │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  react-grid-layout (drag & drop)                    │ │
│  │                                                     │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │ │
│  │  │StatCard │ │StatCard │ │StatCard │ │StatCard │  │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │ │
│  │  ┌───────────────────────────────────────────────┐  │ │
│  │  │  BarChart / PieChart / LineChart               │  │ │
│  │  └───────────────────────────────────────────────┘  │ │
│  │  ┌──────────────────┐ ┌──────────────────┐         │ │
│  │  │  Table            │ │  Table            │         │ │
│  │  └──────────────────┘ └──────────────────┘         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────┐  Chatbot Floating                │
│  │ 💬 AgentFlow       │  (bottom-right)                  │
│  │ ─────────────────  │                                  │
│  │ msg: ...           │                                  │
│  │ [Scrivi...]  [↑]   │                                  │
│  └────────────────────┘                                  │
└─────────────────────────────────────────────────────────┘
```

## DB Schema (additivo)

```sql
CREATE TABLE dashboard_layouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    name VARCHAR(100) DEFAULT 'default',
    year INTEGER DEFAULT 2024,
    widgets JSON NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, user_id, name)
);
```

## Widget JSON Schema

```json
{
  "id": "w-uuid",
  "type": "stat_card|bar_chart|pie_chart|line_chart|table|alert",
  "title": "Fatturato YTD",
  "data_source": "yearly_stats",
  "data_path": "fatture_attive.totale",
  "config": {
    "format": "currency|number|percent",
    "color": "green|blue|orange|red|gray",
    "x_key": "mese",
    "y_keys": ["attive_totale"],
    "columns": ["nome", "count", "totale"]
  },
  "layout": { "x": 0, "y": 0, "w": 3, "h": 2 }
}
```

## API Endpoints (additivi)

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/dashboard/layout` | GET | Leggi layout utente |
| `/dashboard/layout` | PUT | Salva layout utente |
| `/dashboard/layout/reset` | POST | Reset a default |

## Tool orchestratore

```python
{
    "name": "modify_dashboard",
    "description": "Aggiunge, rimuove o modifica un widget nella dashboard dell'utente",
    "parameters": {
        "action": "add|remove|update",
        "widget": { "type": "...", "title": "...", "data_source": "...", ... }
    }
}
```

## Frontend

- `react-grid-layout` per drag & drop
- Widget renderer: switch su `widget.type` → componente React
- Chatbot floating: componente fisso `position: fixed; bottom: 20px; right: 20px`
- Default layout generato dal backend al primo accesso

## Default Layout

```json
[
  { "id": "w1", "type": "stat_card", "title": "Fatture Emesse", "data_source": "yearly_stats", "data_path": "fatture_attive.totale", "config": {"format": "currency", "color": "green", "subtitle_path": "fatture_attive.count", "subtitle_suffix": " fatture"}, "layout": {"x":0,"y":0,"w":3,"h":2} },
  { "id": "w2", "type": "stat_card", "title": "Fatture Ricevute", "data_source": "yearly_stats", "data_path": "fatture_passive.totale", "config": {"format": "currency", "color": "orange", "subtitle_path": "fatture_passive.count", "subtitle_suffix": " fatture"}, "layout": {"x":3,"y":0,"w":3,"h":2} },
  { "id": "w3", "type": "stat_card", "title": "Margine Lordo", "data_source": "yearly_stats", "data_path": "margine_lordo", "config": {"format": "currency", "color": "blue"}, "layout": {"x":6,"y":0,"w":3,"h":2} },
  { "id": "w4", "type": "bar_chart", "title": "Fatturato Mensile", "data_source": "yearly_stats", "data_path": "fatture_per_mese", "config": {"x_key": "mese_label", "y_keys": [{"key": "attive_totale", "color": "#22c55e", "name": "Emesse"}, {"key": "passive_totale", "color": "#f97316", "name": "Ricevute"}]}, "layout": {"x":0,"y":2,"w":12,"h":4} },
  { "id": "w5", "type": "table", "title": "Top 10 Clienti", "data_source": "yearly_stats", "data_path": "top_clienti", "config": {"columns": [{"key":"nome","label":"Cliente"},{"key":"count","label":"Fatt."},{"key":"totale","label":"Totale","format":"currency"}]}, "layout": {"x":0,"y":6,"w":6,"h":4} },
  { "id": "w6", "type": "table", "title": "Top 10 Fornitori", "data_source": "yearly_stats", "data_path": "top_fornitori", "config": {"columns": [{"key":"nome","label":"Fornitore"},{"key":"count","label":"Fatt."},{"key":"totale","label":"Totale","format":"currency"}]}, "layout": {"x":6,"y":6,"w":6,"h":4} }
]
```
