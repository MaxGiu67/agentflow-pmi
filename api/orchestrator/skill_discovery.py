"""Skill discovery — generates help message listing agent capabilities (US-A10)."""


def get_skill_discovery_message(agent_configs: list[dict] | None = None) -> str:
    """Generate a help message listing available agent capabilities.

    Args:
        agent_configs: Optional list of agent config dicts with keys
            agent_type, display_name, enabled. If provided, disabled agents
            are hidden and display_name overrides the default.

    Returns:
        Formatted multi-line string describing what the system can do.
    """
    capabilities = {
        "fisco": "Fatture (emesse e ricevute), scadenze fiscali, F24, ritenute, bollo",
        "conta": "Scritture contabili, piano dei conti, bilancio, registrazioni",
        "cashflow": "Previsioni cash flow a 90 giorni, alert soglia critica",
        "controller": "Import saldi bilancio, creazione budget, EBITDA, analisi scostamenti",
        "conto_economico": "Setup piano conti personalizzato per la tua azienda",
        "normativo": "Monitor aggiornamenti normativi (GU, circolari AdE)",
    }

    icons = {
        "fisco": "\U0001f4cb",
        "conta": "\U0001f4d2",
        "cashflow": "\U0001f4b0",
        "controller": "\U0001f3af",
        "conto_economico": "\U0001f3d7\ufe0f",
        "normativo": "\u2696\ufe0f",
    }

    lines: list[str] = ["Ecco cosa posso fare per te:\n"]

    for agent_type, desc in capabilities.items():
        name = agent_type
        if agent_configs:
            config = next(
                (c for c in agent_configs if c.get("agent_type") == agent_type),
                None,
            )
            if config:
                if not config.get("enabled", True):
                    continue
                name = config.get("display_name", agent_type)
        icon = icons.get(agent_type, "\U0001f916")
        lines.append(f"{icon} **{name}** — {desc}")

    lines.append("\nProva a chiedermi qualcosa come:")
    lines.append('- "Quante fatture ho ricevuto questo mese?"')
    lines.append('- "Quali fatture devo ancora verificare?"')
    lines.append('- "Come sta il mio cash flow?"')
    lines.append('- "Prossime scadenze fiscali"')
    lines.append('- "Aiutami a importare i saldi del bilancio"')
    lines.append('- "Creiamo il budget 2026"')
    lines.append('- "Riepilogo della mia situazione"')

    return "\n".join(lines)
