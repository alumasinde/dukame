"""Contract tests for hardened Daraja STK / per-store M-Pesa config."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.modules.commerce.mpesa import (
    amount_kes_from_minor,
    mpesa_msisdn,
    validate_daraja_config,
)


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def _valid_config(**overrides: str) -> dict[str, str]:
    base = {
        "consumer_key": "test_consumer_key_xx",
        "consumer_secret": "test_consumer_secret_xx",
        "shortcode": "174379",
        "passkey": "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919",
        "environment": "sandbox",
        "transaction_type": "CustomerPayBillOnline",
        "account_reference": "DukaMe",
        "transaction_desc": "Order pay",
    }
    base.update(overrides)
    return base


def test_validate_daraja_config_accepts_valid_sandbox() -> None:
    cleaned = validate_daraja_config(_valid_config())
    assert cleaned["environment"] == "sandbox"
    assert cleaned["shortcode"] == "174379"


def test_validate_daraja_config_rejects_bad_shortcode() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_daraja_config(_valid_config(shortcode="12"))
    assert exc.value.status_code == 422


def test_validate_daraja_config_rejects_placeholder_secret() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_daraja_config(_valid_config(consumer_secret="changeme"))
    assert exc.value.status_code == 422


def test_validate_daraja_config_requires_https_callback_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config as config_mod

    monkeypatch.setattr(config_mod.settings, "environment", "production")
    with pytest.raises(HTTPException) as exc:
        validate_daraja_config(_valid_config(), callback_url="http://example.com/callback")
    assert exc.value.status_code == 503


def test_mpesa_msisdn_normalizes_local_format() -> None:
    assert mpesa_msisdn("0712345678") == "254712345678"
    assert mpesa_msisdn("+254712345678") == "254712345678"


def test_mpesa_msisdn_rejects_invalid() -> None:
    with pytest.raises(HTTPException):
        mpesa_msisdn("12345")


def test_amount_kes_from_minor() -> None:
    assert amount_kes_from_minor(100) == 1
    assert amount_kes_from_minor(25000) == 250
    with pytest.raises(HTTPException):
        amount_kes_from_minor(50)
    with pytest.raises(HTTPException):
        amount_kes_from_minor(150)  # fractional KES not allowed for STK


def test_stk_client_and_callback_hardening_present() -> None:
    mpesa = read("app/modules/commerce/mpesa.py")
    service = read("app/modules/commerce/payment_service.py")
    assert "validate_daraja_config" in mpesa
    assert "stk_query" in mpesa
    assert "CheckoutRequestID" in mpesa
    assert "attempt.payment.store_id != method.store_id" in service
    assert "callback_token_hash(callback_token) != payment.payment_method.callback_token_hash" in service
    assert "validate_daraja_config" in service
