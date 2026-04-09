"""Offer generator — python-docx template engine for Nexa Data offers.

Handles Word XML split-run placeholders: {{Placeholder}} may be split across
multiple XML runs as {{, Placeholder, }} in separate <w:r> elements.
This engine recombines runs, replaces placeholders, and produces a .docx.

Template: api/agents/templates/Template_Offerta_NexaData.docx
See: api/agents/templates/ISTRUZIONI_TEMPLATE.md for placeholder list.
"""

from __future__ import annotations

import copy
import logging
import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn

logger = logging.getLogger(__name__)

# Resolve template path relative to this file
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
DEFAULT_TEMPLATE = _TEMPLATE_DIR / "Template_Offerta_NexaData.docx"

# Regex to find {{PLACEHOLDER}} tokens
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")

# All 31 known placeholders from ISTRUZIONI_TEMPLATE.md
KNOWN_PLACEHOLDERS: set[str] = {
    # Cover page (9)
    "PROTOCOLLO", "DATA_OFFERTA", "NOME_CLIENTE", "INDIRIZZO_CLIENTE",
    "CAP_CITTA_CLIENTE", "PROVINCIA_CLIENTE", "REFERENTE_CLIENTE",
    "TITOLO_OFFERTA", "TESTO_INTRODUTTIVO",
    # Sez. 1 - Descrizione Offerta (5)
    "Descrizione_Offerta", "TECNOLOGIE_INTRO", "TECNOLOGIE_BACKEND",
    "TECNOLOGIE_FRONTEND", "TECNOLOGIE_CONCLUSIONE",
    # Sez. 2 - Componenti
    "Componenti_del_sistema",
    # Sez. 3 - Team
    "Team_di_progetto",
    # Sez. 4 - Stima
    "Stima_dettagliata_di_impegno",
    # Sez. 5 - Piano
    "PIANO_DI_SVILUPPO",
    # Sez. 6 - Modalita contrattuale
    "MODALITA_CONTRATTUALE",
    # Sez. 7 - Assunzioni
    "ASSUNZIONE",
    # Sez. 8 - Rischi
    "RISCHIO",
    # Riferimenti (10)
    "REF_COMMERCIALE_NOME", "REF_COMMERCIALE_EMAIL", "REF_COMMERCIALE_TEL",
    "REF_IT_NOME", "REF_IT_EMAIL", "REF_IT_TEL",
    "REF_AMM_NOME", "REF_AMM_EMAIL", "REF_AMM_TEL",
    "FIRMATARIO",
}


# ── Split-run handling ──────────────────────────────────


def _get_run_text(run_elem: Any) -> str:
    """Extract all text from a <w:r> element (may have multiple <w:t>)."""
    texts = []
    for t in run_elem.findall(qn("w:t")):
        texts.append(t.text or "")
    return "".join(texts)


def _set_run_text(run_elem: Any, text: str) -> None:
    """Set text of a <w:r> element. Clears existing <w:t> nodes and creates one."""
    # Remove all existing <w:t> elements
    for t in run_elem.findall(qn("w:t")):
        run_elem.remove(t)
    # Create new <w:t> with xml:space="preserve" to keep whitespace
    new_t = copy.deepcopy(run_elem.makeelement(qn("w:t"), {}))
    new_t.text = text
    new_t.set(qn("xml:space"), "preserve")
    run_elem.append(new_t)


def _merge_and_replace_in_paragraph(paragraph_elem: Any, replacements: dict[str, str]) -> int:
    """Process a <w:p> element: merge split-run placeholders and replace.

    Word often splits {{Placeholder}} across multiple <w:r> elements.
    Strategy:
    1. Concatenate text from all runs to find placeholders.
    2. Build a mapping from character index in full text to (run_index, char_offset).
    3. For each placeholder found, identify which runs are involved.
    4. Replace the text in the first run, clear the others.

    Returns the number of replacements made.
    """
    runs = paragraph_elem.findall(qn("w:r"))
    if not runs:
        return 0

    # Build full text and char-to-run index map
    full_text = ""
    char_map: list[tuple[int, int]] = []  # (run_idx, offset_in_run)
    for run_idx, run in enumerate(runs):
        run_text = _get_run_text(run)
        for char_idx, _ in enumerate(run_text):
            char_map.append((run_idx, char_idx))
        full_text += run_text

    if not full_text:
        return 0

    count = 0
    # Find all placeholders in the concatenated text
    for match in _PLACEHOLDER_RE.finditer(full_text):
        placeholder_name = match.group(1)
        if placeholder_name not in replacements:
            continue

        start_pos = match.start()
        end_pos = match.end()  # exclusive

        # Ensure positions are within char_map bounds
        if start_pos >= len(char_map) or end_pos - 1 >= len(char_map):
            continue

        # Find which runs are involved
        first_run_idx = char_map[start_pos][0]
        last_run_idx = char_map[end_pos - 1][0]

        replacement_text = replacements[placeholder_name]

        if first_run_idx == last_run_idx:
            # Simple case: entire placeholder in one run
            run = runs[first_run_idx]
            old_text = _get_run_text(run)
            new_text = old_text[:char_map[start_pos][1]] + replacement_text + old_text[char_map[end_pos - 1][1] + 1:]
            _set_run_text(run, new_text)
        else:
            # Split-run case: placeholder spans multiple runs
            # First run: keep text before placeholder, append replacement
            first_run = runs[first_run_idx]
            first_text = _get_run_text(first_run)
            prefix = first_text[:char_map[start_pos][1]]
            _set_run_text(first_run, prefix + replacement_text)

            # Middle runs: clear completely
            for mid_idx in range(first_run_idx + 1, last_run_idx):
                _set_run_text(runs[mid_idx], "")

            # Last run: keep text after placeholder
            last_run = runs[last_run_idx]
            last_text = _get_run_text(last_run)
            suffix = last_text[char_map[end_pos - 1][1] + 1:]
            _set_run_text(last_run, suffix)

        count += 1

    return count


def _replace_in_element(element: Any, replacements: dict[str, str]) -> int:
    """Recursively replace placeholders in all paragraphs of an element."""
    total = 0
    for para in element.iter(qn("w:p")):
        total += _merge_and_replace_in_paragraph(para, replacements)
    return total


# ── Public API ──────────────────────────────────────────


def generate_offer_document(
    replacements: dict[str, str],
    output_path: str | Path,
    template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Generate a Word offer document by replacing placeholders in the template.

    Args:
        replacements: dict mapping placeholder names to their values.
            Keys should match KNOWN_PLACEHOLDERS (without {{ }}).
            Example: {"NOME_CLIENTE": "Acme S.r.l.", "PROTOCOLLO": "ND.ENG.2026.100"}
        output_path: path where the generated .docx will be saved.
        template_path: optional custom template. Defaults to the standard Nexa Data template.

    Returns:
        dict with keys:
            - "output_path": str, absolute path to generated file
            - "replaced": int, number of placeholders successfully replaced
            - "missing": list[str], placeholders in template but not in replacements
            - "unknown": list[str], keys in replacements not in KNOWN_PLACEHOLDERS
            - "error": str or None
    """
    tpl = Path(template_path) if template_path else DEFAULT_TEMPLATE

    if not tpl.exists():
        return {
            "output_path": str(output_path),
            "replaced": 0,
            "missing": [],
            "unknown": [],
            "error": f"Template not found: {tpl}",
        }

    # Validate replacement keys
    unknown_keys = [k for k in replacements if k not in KNOWN_PLACEHOLDERS]
    if unknown_keys:
        logger.warning("Unknown placeholder keys (will be ignored): %s", unknown_keys)

    # Filter to known keys only
    clean_replacements = {k: v for k, v in replacements.items() if k in KNOWN_PLACEHOLDERS}

    try:
        doc = Document(str(tpl))
    except Exception as e:
        return {
            "output_path": str(output_path),
            "replaced": 0,
            "missing": [],
            "unknown": unknown_keys,
            "error": f"Failed to open template: {e}",
        }

    total_replaced = 0

    # 1. Replace in document body
    total_replaced += _replace_in_element(doc.element.body, clean_replacements)

    # 2. Replace in headers and footers
    for section in doc.sections:
        for header in [section.header, section.first_page_header]:
            if header and header.is_linked_to_previous is False:
                total_replaced += _replace_in_element(header._element, clean_replacements)
        for footer in [section.footer, section.first_page_footer]:
            if footer and footer.is_linked_to_previous is False:
                total_replaced += _replace_in_element(footer._element, clean_replacements)

    # 3. Determine which placeholders were NOT provided
    missing = [p for p in KNOWN_PLACEHOLDERS if p not in clean_replacements]

    # Save output
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc.save(str(out))
    except Exception as e:
        return {
            "output_path": str(output_path),
            "replaced": total_replaced,
            "missing": sorted(missing),
            "unknown": sorted(unknown_keys),
            "error": f"Failed to save document: {e}",
        }

    logger.info(
        "Offer generated: %s — %d placeholders replaced, %d missing",
        out.name, total_replaced, len(missing),
    )

    return {
        "output_path": str(out.resolve()),
        "replaced": total_replaced,
        "missing": sorted(missing),
        "unknown": sorted(unknown_keys),
        "error": None,
    }


def list_placeholders(template_path: str | Path | None = None) -> list[str]:
    """Scan the template and return all {{PLACEHOLDER}} names found.

    Useful for validating which placeholders are actually present in the .docx.
    """
    tpl = Path(template_path) if template_path else DEFAULT_TEMPLATE
    if not tpl.exists():
        return []

    doc = Document(str(tpl))
    found: set[str] = set()

    # Scan body
    for para in doc.element.body.iter(qn("w:p")):
        runs = para.findall(qn("w:r"))
        full_text = "".join(_get_run_text(r) for r in runs)
        for m in _PLACEHOLDER_RE.finditer(full_text):
            found.add(m.group(1))

    # Scan headers/footers
    for section in doc.sections:
        for hf in [section.header, section.footer, section.first_page_header, section.first_page_footer]:
            if hf:
                for para in hf._element.iter(qn("w:p")):
                    runs = para.findall(qn("w:r"))
                    full_text = "".join(_get_run_text(r) for r in runs)
                    for m in _PLACEHOLDER_RE.finditer(full_text):
                        found.add(m.group(1))

    return sorted(found)
