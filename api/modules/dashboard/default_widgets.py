"""Default dashboard widget definitions."""

DEFAULT_WIDGETS: list[dict] = [
    {
        "id": "w1",
        "type": "stat_card",
        "title": "Fatture Emesse",
        "data_source": "yearly_stats",
        "data_path": "fatture_attive.totale",
        "config": {
            "format": "currency",
            "color": "green",
            "subtitle_path": "fatture_attive.count",
            "subtitle_suffix": " fatture",
        },
        "layout": {"x": 0, "y": 0, "w": 3, "h": 2},
    },
    {
        "id": "w2",
        "type": "stat_card",
        "title": "Fatture Ricevute",
        "data_source": "yearly_stats",
        "data_path": "fatture_passive.totale",
        "config": {
            "format": "currency",
            "color": "orange",
            "subtitle_path": "fatture_passive.count",
            "subtitle_suffix": " fatture",
        },
        "layout": {"x": 3, "y": 0, "w": 3, "h": 2},
    },
    {
        "id": "w3",
        "type": "stat_card",
        "title": "Margine Lordo",
        "data_source": "yearly_stats",
        "data_path": "margine_lordo",
        "config": {
            "format": "currency",
            "color": "blue",
        },
        "layout": {"x": 6, "y": 0, "w": 3, "h": 2},
    },
    {
        "id": "w4",
        "type": "stat_card",
        "title": "IVA Netta",
        "data_source": "yearly_stats",
        "data_path": "iva_netta",
        "config": {
            "format": "currency",
            "color": "gray",
        },
        "layout": {"x": 9, "y": 0, "w": 3, "h": 2},
    },
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
        "layout": {"x": 0, "y": 2, "w": 12, "h": 4},
    },
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
        "layout": {"x": 0, "y": 6, "w": 6, "h": 4},
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
        "layout": {"x": 6, "y": 6, "w": 6, "h": 4},
    },
]
