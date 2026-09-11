from app.modules.commerce.notifications import normalize_phone
from app.modules.commerce.tracking import tracking_token, tracking_token_hash, verify_tracking_token


def test_kenyan_phone_normalization() -> None:
    assert normalize_phone("0712 345 678") == "+254712345678"
    assert normalize_phone("0112-345-678") == "+254112345678"
    assert normalize_phone("254712345678") == "+254712345678"


def test_tracking_token_is_signed_and_tamper_evident() -> None:
    token = tracking_token("0123456789abcdef0123456789abcdef")
    assert verify_tracking_token("0123456789abcdef0123456789abcdef", token)
    assert not verify_tracking_token("fedcba9876543210fedcba9876543210", token)
    assert tracking_token_hash(token) != tracking_token_hash(token + "x")
