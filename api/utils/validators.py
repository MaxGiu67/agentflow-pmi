"""Validators for Italian fiscal data: P.IVA, Codice Fiscale, ATECO."""


def validate_piva(piva: str) -> tuple[bool, str]:
    """Validate Italian P.IVA (11 digits + Luhn checksum).

    Returns (is_valid, error_message).
    """
    if not piva:
        return False, "P.IVA obbligatoria"

    if not piva.isdigit():
        return False, "P.IVA deve contenere solo cifre"

    if len(piva) != 11:
        return False, f"P.IVA deve avere 11 cifre (inserite {len(piva)})"

    # Luhn-like checksum for Italian P.IVA
    total = 0
    for i, digit in enumerate(piva):
        d = int(digit)
        if i % 2 == 0:
            total += d
        else:
            doubled = d * 2
            total += doubled if doubled <= 9 else doubled - 9
    if total % 10 != 0:
        return False, "P.IVA non valida (checksum errato)"

    return True, ""


# Top-level ATECO codes (2-digit sections and common 2-digit divisions)
# In production this would be a full database table, but for MVP we validate format
# and check against the most common codes
ATECO_SECTIONS = {
    "01", "02", "03",  # Agricoltura
    "05", "06", "07", "08", "09",  # Estrazione
    "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",  # Manifatturiero
    "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
    "30", "31", "32", "33",  # Manifatturiero
    "35",  # Energia
    "36", "37", "38", "39",  # Acqua/rifiuti
    "41", "42", "43",  # Costruzioni
    "45", "46", "47",  # Commercio
    "49", "50", "51", "52", "53",  # Trasporto
    "55", "56",  # Alloggio/ristorazione
    "58", "59", "60", "61", "62", "63",  # ICT
    "64", "65", "66",  # Finanza
    "68",  # Immobiliare
    "69", "70", "71", "72", "73", "74", "75",  # Professioni
    "77", "78", "79", "80", "81", "82",  # Servizi
    "84",  # PA
    "85",  # Istruzione
    "86", "87", "88",  # Sanita
    "90", "91", "92", "93",  # Arte/sport
    "94", "95", "96",  # Altri servizi
    "97", "98", "99",  # Famiglie/organizzazioni
}


def validate_ateco(codice: str) -> tuple[bool, str]:
    """Validate ATECO code format (XX.XX.XX or XX.XX).

    Returns (is_valid, error_message).
    """
    if not codice:
        return True, ""  # ATECO is optional

    # Remove dots for analysis
    parts = codice.split(".")
    if len(parts) not in (2, 3):
        return False, f"Formato ATECO non valido: atteso XX.XX o XX.XX.XX (ricevuto '{codice}')"

    for part in parts:
        if not part.isdigit() or len(part) != 2:
            return False, f"Formato ATECO non valido: ogni sezione deve essere di 2 cifre (ricevuto '{codice}')"

    # Check top-level section exists
    section = parts[0]
    if section not in ATECO_SECTIONS:
        # Find similar sections
        similar = sorted(s for s in ATECO_SECTIONS if s[0] == section[0])[:5]
        suggestion = f" Codici simili: {', '.join(similar)}" if similar else ""
        return False, f"Sezione ATECO '{section}' non riconosciuta.{suggestion}"

    return True, ""
