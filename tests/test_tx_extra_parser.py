"""Test parser extra/description transazioni A-Cube (US-OB-09)."""

from __future__ import annotations

from api.modules.banking.tx_extra_parser import parse_tx_extra


def test_extract_cro_from_extra_dict():
    out = parse_tx_extra(extra={"cro": "12345678901"}, description=None)
    assert out["cro"] == "12345678901"


def test_extract_trn_from_alt_key():
    out = parse_tx_extra(extra={"endToEndId": "ABC-END2END-REF-XYZ-2026"}, description=None)
    assert out["cro"] == "ABC-END2END-REF-XYZ-2026"


def test_extract_cro_from_description_intesa_style():
    out = parse_tx_extra(
        extra=None,
        description="BONIFICO A VOSTRO FAVORE CRO: 12345678901 ORDINANTE ACME SPA",
    )
    assert out["cro"] == "12345678901"


def test_extract_cro_description_no_colon():
    out = parse_tx_extra(
        extra=None,
        description="PAGAMENTO SEPA CRO 98765432100 CAUSALE FATTURA 42/2026",
    )
    assert out["cro"] == "98765432100"


def test_extract_trn_description():
    out = parse_tx_extra(
        extra=None,
        description="INCASSO TRN: IT01SPGE262026A1B2C3D4E5F6G7H8I9",
    )
    assert out["trn"] == "IT01SPGE262026A1B2C3D4E5F6G7H8I9"


def test_extract_invoice_ref_fattura():
    out = parse_tx_extra(
        extra=None,
        description="PAGAMENTO FATTURA N. 42/2026 DEL 15.03.2026",
    )
    assert out["invoice_ref"] == "42/2026"


def test_extract_invoice_ref_ft_shortform():
    out = parse_tx_extra(
        extra=None,
        description="Saldo FT 123-A del 12/04/2026",
    )
    assert out["invoice_ref"] == "123-A"


def test_extract_invoice_ref_invoice_english():
    out = parse_tx_extra(
        extra=None,
        description="Payment Invoice #INV-2026-0042 from ACME Ltd",
    )
    assert out["invoice_ref"] == "INV-2026-0042"


def test_extra_dict_preferred_over_description():
    out = parse_tx_extra(
        extra={"cro": "99999999999"},
        description="CRO: 11111111111",
    )
    assert out["cro"] == "99999999999"  # extra vince


def test_all_none_when_nothing_matches():
    out = parse_tx_extra(extra=None, description="Spesa generica senza riferimenti")
    assert out == {"cro": None, "trn": None, "invoice_ref": None}


def test_extra_not_dict_ignored():
    """Se A-Cube ritorna extra come stringa/lista non crasha."""
    out = parse_tx_extra(extra="random string", description="CRO 12345678901")
    assert out["cro"] == "12345678901"


def test_all_fields_combined():
    out = parse_tx_extra(
        extra=None,
        description="BONIFICO SEPA CRO: 12345678901 TRN: IT02BANK2026XYZABCDEF0123456789 FATT N. 77/2026",
    )
    assert out["cro"] == "12345678901"
    assert out["trn"] == "IT02BANK2026XYZABCDEF0123456789"
    assert out["invoice_ref"] == "77/2026"
