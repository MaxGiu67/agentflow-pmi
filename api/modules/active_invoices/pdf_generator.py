"""PDF Copia di Cortesia generator for active invoices (US-43).

Generates a professional PDF from invoice data (not from XML).
Uses reportlab for PDF generation.
"""

import io
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Modalità pagamento labels
MP_LABELS = {
    "MP01": "Contanti", "MP02": "Assegno", "MP03": "Assegno circolare",
    "MP05": "Bonifico bancario", "MP08": "Carta di pagamento",
    "MP12": "RIBA", "MP19": "SEPA Direct Debit", "MP23": "PagoPA",
}


def generate_courtesy_pdf(
    tenant_name: str,
    tenant_piva: str,
    tenant_sede: str | None,
    tenant_email: str | None,
    tenant_pec: str | None,
    tenant_telefono: str | None,
    numero_fattura: str,
    data_fattura: date,
    document_type: str,
    cliente_nome: str,
    cliente_piva: str,
    cliente_sede: str | None,
    linee: list[dict],
    importo_netto: float,
    importo_iva: float,
    importo_totale: float,
    modalita_pagamento: str | None,
    iban: str | None,
    banca_nome: str | None,
    scadenza_pagamento: str | None,
) -> bytes:
    """Generate a PDF courtesy copy. Returns PDF bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16, spaceAfter=6)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    normal = styles["Normal"]
    bold_style = ParagraphStyle("Bold", parent=normal, fontName="Helvetica-Bold")
    small_style = ParagraphStyle("Small", parent=normal, fontSize=8)

    elements = []

    # Header — Disclaimer
    elements.append(Paragraph("COPIA DI CORTESIA — Documento privo di valore fiscale", subtitle_style))
    elements.append(Spacer(1, 4 * mm))

    # Document type label
    doc_labels = {"TD01": "FATTURA", "TD04": "NOTA DI CREDITO", "TD24": "FATTURA DIFFERITA", "TD06": "PARCELLA"}
    doc_label = doc_labels.get(document_type, "FATTURA")
    elements.append(Paragraph(f"{doc_label} N. {numero_fattura}", title_style))
    elements.append(Paragraph(f"Data: {data_fattura.strftime('%d/%m/%Y')}", normal))
    elements.append(Spacer(1, 6 * mm))

    # Emittente + Cliente side by side
    emit_text = f"<b>{tenant_name}</b><br/>P.IVA: {tenant_piva}"
    if tenant_sede:
        emit_text += f"<br/>{tenant_sede}"
    if tenant_telefono:
        emit_text += f"<br/>Tel: {tenant_telefono}"
    if tenant_email:
        emit_text += f"<br/>{tenant_email}"
    if tenant_pec:
        emit_text += f"<br/>PEC: {tenant_pec}"

    cli_text = f"<b>{cliente_nome}</b>"
    if cliente_piva:
        cli_text += f"<br/>P.IVA: {cliente_piva}"
    if cliente_sede:
        cli_text += f"<br/>{cliente_sede}"

    header_data = [[
        Paragraph(emit_text, small_style),
        Paragraph(cli_text, small_style),
    ]]
    header_table = Table(header_data, colWidths=[250, 250])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8 * mm))

    # Line items table
    table_data = [["#", "Descrizione", "Q.tà", "Prezzo Unit.", "IVA %", "Totale"]]
    for i, linea in enumerate(linee, 1):
        qta = linea.get("quantita", 1)
        prezzo = linea.get("prezzo_unitario", 0)
        aliq = linea.get("aliquota_iva", 22)
        tot = round(qta * prezzo, 2)
        table_data.append([
            str(i),
            linea.get("descrizione", "")[:60],
            f"{qta:.2f}",
            f"€ {prezzo:,.2f}",
            f"{aliq:.0f}%",
            f"€ {tot:,.2f}",
        ])

    t = Table(table_data, colWidths=[25, 200, 45, 80, 40, 80])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 4 * mm))

    # Totals
    totals_data = [
        ["", "Imponibile:", f"€ {importo_netto:,.2f}"],
        ["", "IVA:", f"€ {importo_iva:,.2f}"],
        ["", "TOTALE DOCUMENTO:", f"€ {importo_totale:,.2f}"],
    ]
    tt = Table(totals_data, colWidths=[300, 100, 80])
    tt.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (1, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (1, 2), (-1, 2), 1, colors.black),
    ]))
    elements.append(tt)
    elements.append(Spacer(1, 8 * mm))

    # Payment info
    mp_label = MP_LABELS.get(modalita_pagamento or "", modalita_pagamento or "")
    pay_text = f"<b>Modalità pagamento:</b> {mp_label}"
    if iban:
        pay_text += f"<br/><b>IBAN:</b> {iban}"
    if banca_nome:
        pay_text += f" ({banca_nome})"
    if scadenza_pagamento:
        pay_text += f"<br/><b>Scadenza:</b> {scadenza_pagamento}"
    elements.append(Paragraph(pay_text, normal))

    # Build PDF
    doc.build(elements)
    return buffer.getvalue()
