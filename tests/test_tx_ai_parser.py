"""Test parser AI movimenti bancari (Sprint 50)."""

from api.modules.banking.tx_ai_parser import parse_with_rules


def test_bonifico_ricevuto_qubika():
    desc = (
        "ACCR BON ISTANT COD. DISP.: 0126040163715019 CASH PhLoSu3O010420262004071 "
        "Acconto pagamento fattura Bonifico a Vostro favore disposto da: "
        "MITT.: QUBIKA S.R.L. BENEF.: TAAL SRL BIC. ORD.: CCRTIT2TN00"
    )
    r = parse_with_rules(desc, "credit", 1000.0)
    assert "QUBIKA" in (r.counterparty or "").upper()
    assert r.category == "income_invoice"
    assert r.confidence >= 0.5


def test_bonifico_inviato_prestitalia():
    desc = (
        "ADDEBITO BON IST 0126040163715700 Bonifico da Voi disposto a favore di: "
        "Prestitalia s.p.a. Seconda rata numero di contratto (4900368489)"
    )
    r = parse_with_rules(desc, "debit", -1000.0)
    assert r.category == "loan_payment"
    assert r.subcategory == "rata_prestito"


def test_canone_mensile():
    desc = "CANONE MENSILE CANONE MENSILE MESE DI MARZO"
    r = parse_with_rules(desc, "debit", -10.0)
    assert r.category == "fee"
    assert r.subcategory == "canone"


def test_premio_polizza():
    desc = "PREMIO POLIZZA ADDEBITO PREMI POLIZZA ID:GC105-20260331"
    r = parse_with_rules(desc, "debit", -86.32)
    assert r.category == "fee"
    assert r.subcategory == "polizza"


def test_assegno():
    desc = "ASSEGNO N. 786 Assegno N. 9376791786"
    r = parse_with_rules(desc, "debit", -1400.0)
    # Assegno non ha categoria specifica nel pattern → other o expense_invoice
    assert r.category in ("other", "expense_invoice")


def test_invoice_ref_extraction():
    desc = "BONIFICO Saldo fattura FT 2025/123 da QUBIKA SRL"
    r = parse_with_rules(desc, "credit", 5000.0)
    assert r.invoice_ref is not None
    assert "2025" in r.invoice_ref or "123" in r.invoice_ref


def test_iban_extraction():
    desc = "Bonifico ricevuto IT60X0542811101000000123456 da Mario Rossi"
    r = parse_with_rules(desc, "credit", 100.0)
    assert r.counterparty_iban == "IT60X0542811101000000123456"


def test_f24():
    desc = "ADDEBITO F24 AGENZIA ENTRATE Codice tributo 6099"
    r = parse_with_rules(desc, "debit", -250.0)
    assert r.category == "tax_f24"


def test_stipendio():
    desc = "STIPENDIO MENSILE EMOLUMENTI Mario Rossi"
    r = parse_with_rules(desc, "debit", -2500.0)
    assert r.category == "payroll"


def test_no_description():
    r = parse_with_rules(None, "credit", 100.0)
    assert r.category == "other"
    assert r.confidence == 0.0


def test_low_confidence_random_text():
    r = parse_with_rules("xyz random testo non parsabile", "debit", -50.0)
    assert r.confidence < 0.5
