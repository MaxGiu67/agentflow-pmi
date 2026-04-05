"""Default dashboard widget definitions — role-based."""

# ══════════════════════════════════════════════════════
# ADMIN / OWNER — Full financial overview
# ══════════════════════════════════════════════════════

ADMIN_WIDGETS: list[dict] = [
    # ── Row 1: Big 3 KPI ──
    {
        "id": "a1",
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
        "id": "a2",
        "type": "stat_card",
        "title": "Costi Totali",
        "data_source": "yearly_stats",
        "data_path": "costi_totali",
        "config": {
            "format": "currency",
            "color": "red",
            "subtitle": "fornitori + personale + spese + rate",
        },
        "layout": {"x": 4, "y": 0, "w": 4, "h": 2},
    },
    {
        "id": "a3",
        "type": "stat_card",
        "title": "Margine (EBITDA)",
        "data_source": "yearly_stats",
        "data_path": "margine_lordo",
        "config": {
            "format": "currency",
            "color": "blue",
            "subtitle": "ricavi - costi",
        },
        "layout": {"x": 8, "y": 0, "w": 4, "h": 2},
    },
    # ── Row 2: Ricavi breakdown ──
    {
        "id": "a4",
        "type": "stat_card",
        "title": "Fatture Emesse",
        "data_source": "yearly_stats",
        "data_path": "fatture_attive.imponibile",
        "config": {
            "format": "currency",
            "color": "green",
            "subtitle_path": "fatture_attive.count",
            "subtitle_suffix": " fatture attive",
        },
        "layout": {"x": 0, "y": 2, "w": 4, "h": 2},
    },
    {
        "id": "a5",
        "type": "stat_card",
        "title": "Corrispettivi",
        "data_source": "yearly_stats",
        "data_path": "corrispettivi.totale",
        "config": {
            "format": "currency",
            "color": "emerald",
            "subtitle_path": "corrispettivi.count",
            "subtitle_suffix": " scontrini",
        },
        "layout": {"x": 4, "y": 2, "w": 4, "h": 2},
    },
    {
        "id": "a6",
        "type": "stat_card",
        "title": "IVA Netta",
        "data_source": "yearly_stats",
        "data_path": "iva_netta.saldo",
        "config": {
            "format": "currency",
            "color": "amber",
            "subtitle": "debito - credito = da versare",
        },
        "layout": {"x": 8, "y": 2, "w": 4, "h": 2},
    },
    # ── Row 3: Costi breakdown ──
    {
        "id": "a7",
        "type": "stat_card",
        "title": "Fornitori (Fatt. Passive)",
        "data_source": "yearly_stats",
        "data_path": "fatture_passive.imponibile",
        "config": {
            "format": "currency",
            "color": "orange",
            "subtitle_path": "fatture_passive.count",
            "subtitle_suffix": " fatture ricevute",
        },
        "layout": {"x": 0, "y": 4, "w": 3, "h": 2},
    },
    {
        "id": "a8",
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
        "layout": {"x": 3, "y": 4, "w": 3, "h": 2},
    },
    {
        "id": "a9",
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
        "layout": {"x": 6, "y": 4, "w": 3, "h": 2},
    },
    {
        "id": "a10",
        "type": "stat_card",
        "title": "Rate Finanziamenti",
        "data_source": "yearly_stats",
        "data_path": "finanziamenti.totale_annuo",
        "config": {
            "format": "currency",
            "color": "red",
            "subtitle_path": "finanziamenti.count",
            "subtitle_suffix": " prestiti",
        },
        "layout": {"x": 9, "y": 4, "w": 3, "h": 2},
    },
    # ── Row 4: Monthly chart ricavi vs costi ──
    {
        "id": "a11",
        "type": "bar_chart",
        "title": "Fatturato Mensile (Ricavi vs Costi)",
        "data_source": "yearly_stats",
        "data_path": "fatture_per_mese",
        "config": {
            "x_key": "mese",
            "y_keys": [
                {"key": "attive_totale", "color": "#22c55e", "name": "Ricavi (emesse)"},
                {"key": "passive_totale", "color": "#ef4444", "name": "Costi (ricevute)"},
            ],
        },
        "layout": {"x": 0, "y": 6, "w": 12, "h": 4},
    },
    # ── Row 5: Top clienti & fornitori ──
    {
        "id": "a12",
        "type": "table",
        "title": "Migliori Clienti (per fatturato)",
        "data_source": "yearly_stats",
        "data_path": "top_clienti",
        "config": {
            "columns": [
                {"key": "nome", "label": "Cliente"},
                {"key": "count", "label": "N. Fatt."},
                {"key": "totale", "label": "Totale", "format": "currency"},
            ],
        },
        "layout": {"x": 0, "y": 10, "w": 6, "h": 4},
    },
    {
        "id": "a13",
        "type": "table",
        "title": "Principali Fornitori (per costo)",
        "data_source": "yearly_stats",
        "data_path": "top_fornitori",
        "config": {
            "columns": [
                {"key": "nome", "label": "Fornitore"},
                {"key": "count", "label": "N. Fatt."},
                {"key": "totale", "label": "Totale", "format": "currency"},
            ],
        },
        "layout": {"x": 6, "y": 10, "w": 6, "h": 4},
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
