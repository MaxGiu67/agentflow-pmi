"""Default dashboard widget definitions — role-based."""

# ══════════════════════════════════════════════════════
# ADMIN / OWNER — Full financial overview
# ══════════════════════════════════════════════════════

ADMIN_WIDGETS: list[dict] = [
    # Row 1: Revenue, Costs, EBITDA
    {
        "id": "w1",
        "type": "stat_card",
        "title": "Ricavi Totali",
        "data_source": "yearly_stats",
        "data_path": "ricavi_totali",
        "config": {
            "format": "currency",
            "color": "green",
            "subtitle_path": "fatture_attive.count",
            "subtitle_suffix": " fatture + corrispettivi",
        },
        "layout": {"x": 0, "y": 0, "w": 4, "h": 2},
    },
    {
        "id": "w2",
        "type": "stat_card",
        "title": "Costi Totali",
        "data_source": "yearly_stats",
        "data_path": "costi_totali",
        "config": {
            "format": "currency",
            "color": "orange",
            "subtitle": "fornitori + personale + spese",
        },
        "layout": {"x": 4, "y": 0, "w": 4, "h": 2},
    },
    {
        "id": "w3",
        "type": "stat_card",
        "title": "Margine (EBITDA)",
        "data_source": "yearly_stats",
        "data_path": "margine_lordo",
        "config": {
            "format": "currency",
            "color": "blue",
        },
        "layout": {"x": 8, "y": 0, "w": 4, "h": 2},
    },
    # Row 2: Cost breakdown
    {
        "id": "w_pers",
        "type": "stat_card",
        "title": "Costo Personale",
        "data_source": "yearly_stats",
        "data_path": "costo_personale.totale",
        "config": {
            "format": "currency",
            "color": "purple",
            "subtitle_path": "costo_personale.count",
            "subtitle_suffix": " cedolini",
        },
        "layout": {"x": 0, "y": 2, "w": 3, "h": 2},
    },
    {
        "id": "w_forn",
        "type": "stat_card",
        "title": "Fornitori",
        "data_source": "yearly_stats",
        "data_path": "fatture_passive.totale",
        "config": {
            "format": "currency",
            "color": "orange",
            "subtitle_path": "fatture_passive.count",
            "subtitle_suffix": " fatture",
        },
        "layout": {"x": 3, "y": 2, "w": 3, "h": 2},
    },
    {
        "id": "w_spese",
        "type": "stat_card",
        "title": "Note Spese",
        "data_source": "yearly_stats",
        "data_path": "note_spese.totale",
        "config": {
            "format": "currency",
            "color": "gray",
            "subtitle_path": "note_spese.count",
            "subtitle_suffix": " voci",
        },
        "layout": {"x": 6, "y": 2, "w": 3, "h": 2},
    },
    {
        "id": "w_fin",
        "type": "stat_card",
        "title": "Finanziamenti",
        "data_source": "yearly_stats",
        "data_path": "finanziamenti.totale_annuo",
        "config": {
            "format": "currency",
            "color": "red",
            "subtitle_path": "finanziamenti.count",
            "subtitle_suffix": " prestiti",
        },
        "layout": {"x": 9, "y": 2, "w": 3, "h": 2},
    },
    # Row 3: Monthly chart
    {
        "id": "w5",
        "type": "bar_chart",
        "title": "Fatturato Mensile",
        "data_source": "yearly_stats",
        "data_path": "fatture_per_mese",
        "config": {
            "x_key": "mese",
            "y_keys": [
                {"key": "attive_totale", "color": "#22c55e", "name": "Emesse"},
                {"key": "passive_totale", "color": "#f97316", "name": "Ricevute"},
            ],
        },
        "layout": {"x": 0, "y": 4, "w": 12, "h": 4},
    },
    # Row 4: Top clients & suppliers
    {
        "id": "w6",
        "type": "table",
        "title": "Top 10 Clienti",
        "data_source": "yearly_stats",
        "data_path": "top_clienti",
        "config": {
            "columns": [
                {"key": "nome", "label": "Cliente"},
                {"key": "count", "label": "Fatt."},
                {"key": "totale", "label": "Totale", "format": "currency"},
            ],
        },
        "layout": {"x": 0, "y": 8, "w": 6, "h": 4},
    },
    {
        "id": "w7",
        "type": "table",
        "title": "Top 10 Fornitori",
        "data_source": "yearly_stats",
        "data_path": "top_fornitori",
        "config": {
            "columns": [
                {"key": "nome", "label": "Fornitore"},
                {"key": "count", "label": "Fatt."},
                {"key": "totale", "label": "Totale", "format": "currency"},
            ],
        },
        "layout": {"x": 6, "y": 8, "w": 6, "h": 4},
    },
]


# ══════════════════════════════════════════════════════
# COMMERCIALE — Sales-focused KPIs
# ══════════════════════════════════════════════════════

COMMERCIALE_WIDGETS: list[dict] = [
    # Row 1: My pipeline value, Deals Won, Win Rate
    {
        "id": "c1",
        "type": "stat_card",
        "title": "Pipeline Attiva",
        "data_source": "crm_stats",
        "data_path": "pipeline_value",
        "config": {
            "format": "currency",
            "color": "blue",
            "subtitle_path": "pipeline_count",
            "subtitle_suffix": " deal attivi",
        },
        "layout": {"x": 0, "y": 0, "w": 4, "h": 2},
    },
    {
        "id": "c2",
        "type": "stat_card",
        "title": "Revenue Chiusa",
        "data_source": "crm_stats",
        "data_path": "revenue_won",
        "config": {
            "format": "currency",
            "color": "green",
            "subtitle_path": "deals_won",
            "subtitle_suffix": " deal vinti",
        },
        "layout": {"x": 4, "y": 0, "w": 4, "h": 2},
    },
    {
        "id": "c3",
        "type": "stat_card",
        "title": "Win Rate",
        "data_source": "crm_stats",
        "data_path": "win_rate",
        "config": {
            "format": "percent",
            "color": "purple",
        },
        "layout": {"x": 8, "y": 0, "w": 4, "h": 2},
    },
    # Row 2: Activities, New Contacts, Proposals Sent
    {
        "id": "c4",
        "type": "stat_card",
        "title": "Attivita Questo Mese",
        "data_source": "crm_stats",
        "data_path": "activities_month",
        "config": {
            "format": "number",
            "color": "amber",
            "subtitle": "call, email, meeting",
        },
        "layout": {"x": 0, "y": 2, "w": 4, "h": 2},
    },
    {
        "id": "c5",
        "type": "stat_card",
        "title": "Nuovi Contatti",
        "data_source": "crm_stats",
        "data_path": "new_contacts_month",
        "config": {
            "format": "number",
            "color": "teal",
            "subtitle": "questo mese",
        },
        "layout": {"x": 4, "y": 2, "w": 4, "h": 2},
    },
    {
        "id": "c6",
        "type": "stat_card",
        "title": "Proposte Inviate",
        "data_source": "crm_stats",
        "data_path": "proposals_sent",
        "config": {
            "format": "number",
            "color": "indigo",
            "subtitle": "in attesa di risposta",
        },
        "layout": {"x": 8, "y": 2, "w": 4, "h": 2},
    },
    # Row 3: Pipeline by stage
    {
        "id": "c7",
        "type": "bar_chart",
        "title": "Pipeline per Fase",
        "data_source": "crm_stats",
        "data_path": "pipeline_by_stage",
        "config": {
            "x_key": "stage",
            "y_keys": [
                {"key": "value", "color": "#3b82f6", "name": "Valore"},
                {"key": "count", "color": "#8b5cf6", "name": "N. Deal"},
            ],
        },
        "layout": {"x": 0, "y": 4, "w": 12, "h": 4},
    },
    # Row 4: Top deals in pipeline
    {
        "id": "c8",
        "type": "table",
        "title": "Top Deal Attivi",
        "data_source": "crm_stats",
        "data_path": "top_deals",
        "config": {
            "columns": [
                {"key": "name", "label": "Deal"},
                {"key": "client", "label": "Cliente"},
                {"key": "stage", "label": "Fase"},
                {"key": "value", "label": "Valore", "format": "currency"},
            ],
        },
        "layout": {"x": 0, "y": 8, "w": 12, "h": 4},
    },
]


# Backward compat — DEFAULT_WIDGETS is admin
DEFAULT_WIDGETS = ADMIN_WIDGETS


def get_widgets_for_role(role: str) -> list[dict]:
    """Return appropriate widget set based on user role."""
    if role in ("owner", "admin"):
        return ADMIN_WIDGETS
    elif role == "commerciale":
        return COMMERCIALE_WIDGETS
    else:
        # viewer gets a lite version of admin (read-only)
        return ADMIN_WIDGETS
