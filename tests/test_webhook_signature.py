"""Test utility verifica firma HMAC per webhook (Sprint 48 US-OB-05)."""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest

from api.security.webhook_signature import (
    InvalidSignatureError,
    ReplayAttackError,
    SignatureConfig,
    compute_signature,
    verify_signature,
)


BODY = b'{"fiscalId":"IT12345678901","success":true,"updatedAccounts":["a","b"]}'
SECRET = "super-secret-shared-key"


def _sig_sha256(body: bytes = BODY, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_compute_signature_sha256():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET, algorithm="sha256")
    sig = compute_signature(BODY, config)
    assert sig == _sig_sha256()
    assert len(sig) == 64  # SHA-256 hex


def test_compute_signature_with_prefix():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET, algorithm="sha256", prefix="sha256=")
    sig = compute_signature(BODY, config)
    assert sig.startswith("sha256=")
    assert sig == "sha256=" + _sig_sha256()


def test_compute_signature_sha512():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET, algorithm="sha512")
    sig = compute_signature(BODY, config)
    expected = hmac.new(SECRET.encode(), BODY, hashlib.sha512).hexdigest()
    assert sig == expected
    assert len(sig) == 128


def test_verify_signature_valid():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET)
    verify_signature(BODY, _sig_sha256(), config)  # no raise


def test_verify_signature_invalid_raises():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET)
    with pytest.raises(InvalidSignatureError):
        verify_signature(BODY, "invalid-signature-aaa", config)


def test_verify_signature_missing_raises():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET)
    with pytest.raises(InvalidSignatureError, match="mancante"):
        verify_signature(BODY, None, config)


def test_verify_signature_no_secret_raises():
    config = SignatureConfig(header_name="X-Sig", secret="")
    with pytest.raises(InvalidSignatureError, match="Secret"):
        verify_signature(BODY, _sig_sha256(), config)


def test_verify_signature_body_tampering_detected():
    """Se il body cambia di 1 byte, la firma originale non combacia più."""
    config = SignatureConfig(header_name="X-Sig", secret=SECRET)
    good_sig = _sig_sha256()

    tampered_body = BODY.replace(b'"success":true', b'"success":fals')  # attaccante modifica 1 byte
    with pytest.raises(InvalidSignatureError):
        verify_signature(tampered_body, good_sig, config)


def test_verify_signature_wrong_secret_detected():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET)
    wrong_sig = hmac.new(b"different-secret", BODY, hashlib.sha256).hexdigest()
    with pytest.raises(InvalidSignatureError):
        verify_signature(BODY, wrong_sig, config)


def test_verify_signature_with_prefix():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET, prefix="sha256=")
    sig = "sha256=" + _sig_sha256()
    verify_signature(BODY, sig, config)


def test_verify_signature_prefix_mismatch_fails():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET, prefix="sha256=")
    # firma senza prefisso
    with pytest.raises(InvalidSignatureError):
        verify_signature(BODY, _sig_sha256(), config)


def test_replay_protection_reject_old_timestamp():
    config = SignatureConfig(
        header_name="X-Sig", secret=SECRET,
        max_age_seconds=300, timestamp_header="X-Timestamp",
    )
    old_ts = str(int(time.time()) - 600)  # 10 min fa
    with pytest.raises(ReplayAttackError, match="troppo vecchio"):
        verify_signature(BODY, _sig_sha256(), config, received_timestamp=old_ts)


def test_replay_protection_accept_fresh_timestamp():
    config = SignatureConfig(
        header_name="X-Sig", secret=SECRET,
        max_age_seconds=300, timestamp_header="X-Timestamp",
    )
    fresh_ts = str(int(time.time()))
    verify_signature(BODY, _sig_sha256(), config, received_timestamp=fresh_ts)


def test_replay_protection_reject_future_timestamp():
    """Clock drift > 60s dal futuro è sospetto."""
    config = SignatureConfig(
        header_name="X-Sig", secret=SECRET,
        max_age_seconds=300, timestamp_header="X-Timestamp",
    )
    future_ts = str(int(time.time()) + 120)  # 2 min nel futuro
    with pytest.raises(ReplayAttackError, match="futuro"):
        verify_signature(BODY, _sig_sha256(), config, received_timestamp=future_ts)


def test_invalid_algorithm_raises():
    config = SignatureConfig(header_name="X-Sig", secret=SECRET, algorithm="not_an_algo")
    with pytest.raises(ValueError, match="non supportato"):
        compute_signature(BODY, config)
