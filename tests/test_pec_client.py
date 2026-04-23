"""Unit tests for PEC adapter — presets and receipt filename parsing."""

from __future__ import annotations

import email
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

from api.adapters import pec_client


def test_provider_presets_all_have_ssl_ports():
    for code, p in pec_client.PEC_PROVIDERS.items():
        assert p["smtp_port"] == 465, f"{code} smtp should be SSL 465"
        assert p["imap_port"] == 993, f"{code} imap should be SSL 993"
        assert p["smtp_host"] and p["imap_host"]


def test_get_provider_preset_case_insensitive():
    assert pec_client.get_provider_preset("ARUBA")["label"] == "Aruba PEC"
    assert pec_client.get_provider_preset("unknown") is None


def test_receipt_filename_regex_matches_standard_patterns():
    cases = [
        ("RC_IT12345678901_00001.xml", "RC", "IT12345678901_00001"),
        ("NS_IT99999999999_ABC01.xml", "NS", "IT99999999999_ABC01"),
        ("MC_IT00000000001_00002_001.xml", "MC", "IT00000000001_00002"),
        ("NE_IT12345678901_00001.xml", "NE", "IT12345678901_00001"),
        ("DT_IT12345678901_00001.xml", "DT", "IT12345678901_00001"),
    ]
    for fname, prefix, orig in cases:
        m = pec_client._RECEIPT_FILENAME_RE.search(fname)
        assert m is not None, f"{fname} should match"
        assert m.group("prefix").upper() == prefix
        assert m.group("original") == orig


def test_receipt_regex_rejects_non_receipts():
    assert pec_client._RECEIPT_FILENAME_RE.search("IT12345678901_00001.xml") is None
    assert pec_client._RECEIPT_FILENAME_RE.search("random.pdf") is None


def test_parse_receipt_from_message_with_attachment():
    msg = MIMEMultipart()
    msg["From"] = "servizisdi@pec.fatturapa.it"
    msg["To"] = "me@pec.example.it"
    msg["Subject"] = "Esito fattura"
    msg["Message-ID"] = "<abc123@sdi>"
    msg.attach(MIMEText("body", "plain"))

    att = MIMEApplication(b"<xml/>", _subtype="xml")
    att.add_header("Content-Disposition", "attachment", filename="RC_IT12345678901_00001.xml")
    msg.attach(att)

    parsed = email.message_from_bytes(msg.as_bytes())
    r = pec_client._parse_receipt_message(parsed)
    assert r is not None
    assert r.receipt_type == "RC"
    assert r.related_filename == "IT12345678901_00001.xml"
    assert r.message_id == "<abc123@sdi>"


def test_parse_receipt_from_subject_fallback():
    msg = MIMEMultipart()
    msg["From"] = "servizisdi@pec.fatturapa.it"
    msg["Subject"] = "NS notifica scarto fattura"
    msg["Message-ID"] = "<x@y>"
    msg.attach(MIMEText("body"))
    parsed = email.message_from_bytes(msg.as_bytes())
    r = pec_client._parse_receipt_message(parsed)
    assert r is not None
    assert r.receipt_type == "NS"


def test_parse_receipt_skips_non_receipt_mail():
    msg = MIMEMultipart()
    msg["From"] = "random@someone.it"
    msg["Subject"] = "Ciao"
    msg.attach(MIMEText("hello"))
    parsed = email.message_from_bytes(msg.as_bytes())
    r = pec_client._parse_receipt_message(parsed)
    assert r is None
