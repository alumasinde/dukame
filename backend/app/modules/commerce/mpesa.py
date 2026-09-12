from __future__ import annotations

import base64
import logging
import re
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.modules.commerce.notification_channels import phone_digits

logger = logging.getLogger(__name__)

# Safaricom STK expects MSISDN without '+' (2547XXXXXXXX).
_MSISDN_RE = re.compile(r"^254[17]\d{8}$")
_SHORTCODE_RE = re.compile(r"^\d{5,8}$")

ALLOWED_ENVIRONMENTS = frozenset({"sandbox", "production"})
ALLOWED_TRANSACTION_TYPES = frozenset({"CustomerPayBillOnline", "CustomerBuyGoodsOnline"})


class MpesaProviderError(RuntimeError):
    pass


def mpesa_msisdn(phone: str) -> str:
    """Normalize to Safaricom STK MSISDN (2547… / 2541…)."""
    digits = phone_digits(phone or "")
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    if digits.startswith("254") and len(digits) == 12 and _MSISDN_RE.match(digits):
        return digits
    raise HTTPException(status_code=422, detail="Enter a valid Kenyan M-Pesa phone number")


def amount_kes_from_minor(amount_minor: int) -> int:
    """Convert integer minor units (cents) to whole KES for Daraja Amount."""
    if amount_minor < 100:
        raise HTTPException(status_code=422, detail="Payment amount must be at least 1 KES")
    if amount_minor % 100 != 0:
        # Daraja STK uses whole shillings; reject fractional cents.
        raise HTTPException(status_code=422, detail="Payment amount must be a whole number of KES")
    return amount_minor // 100


def validate_daraja_config(config: dict[str, str], *, callback_url: str | None = None) -> dict[str, str]:
    """Strip and validate per-store Daraja STK config. Returns a cleaned dict."""
    if not config:
        raise HTTPException(status_code=422, detail="M-Pesa configuration is required")

    cleaned: dict[str, str] = {}
    for key, value in config.items():
        if not isinstance(key, str):
            continue
        cleaned[key.strip()] = value.strip() if isinstance(value, str) else str(value).strip()

    required = {
        "consumer_key": "Consumer Key",
        "consumer_secret": "Consumer Secret",
        "shortcode": "Business Shortcode",
        "passkey": "Passkey",
        "environment": "Environment",
        "transaction_type": "Transaction type",
        "account_reference": "Account reference",
        "transaction_desc": "Transaction description",
    }
    missing = [label for key, label in required.items() if not cleaned.get(key)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing M-Pesa fields: {', '.join(missing)}")

    environment = cleaned["environment"].lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise HTTPException(status_code=422, detail="Choose Sandbox or Production for the M-Pesa environment")
    cleaned["environment"] = environment

    transaction_type = cleaned["transaction_type"]
    if transaction_type not in ALLOWED_TRANSACTION_TYPES:
        raise HTTPException(status_code=422, detail="Choose PayBill or Buy Goods for the transaction type")

    shortcode = cleaned["shortcode"]
    if not _SHORTCODE_RE.match(shortcode):
        raise HTTPException(status_code=422, detail="Business Shortcode must be 5–8 digits")

    if len(cleaned["consumer_key"]) < 8 or len(cleaned["consumer_secret"]) < 8:
        raise HTTPException(status_code=422, detail="Consumer Key and Consumer Secret look incomplete")
    if len(cleaned["passkey"]) < 8:
        raise HTTPException(status_code=422, detail="Passkey looks incomplete")

    # Reject obvious placeholders
    lowered_secret = cleaned["consumer_secret"].lower()
    if lowered_secret in {"secret", "password", "changeme", "your_consumer_secret"}:
        raise HTTPException(status_code=422, detail="Replace placeholder M-Pesa credentials with real Daraja values")

    account_reference = cleaned["account_reference"]
    if len(account_reference) > 12:
        raise HTTPException(status_code=422, detail="Account reference must be 12 characters or fewer")
    transaction_desc = cleaned["transaction_desc"]
    if len(transaction_desc) > 13:
        raise HTTPException(status_code=422, detail="Transaction description must be 13 characters or fewer")

    if callback_url is not None:
        if not callback_url.startswith(("https://", "http://")):
            raise HTTPException(status_code=503, detail="M-Pesa callback URL is invalid")
        if settings.is_production and not callback_url.startswith("https://"):
            raise HTTPException(status_code=503, detail="M-Pesa callback URL must use HTTPS in production")

    return cleaned


class MpesaClient:
    def __init__(self, config: dict[str, str], callback_url: str) -> None:
        cleaned = validate_daraja_config(config, callback_url=callback_url)
        self.consumer_key = cleaned["consumer_key"]
        self.consumer_secret = cleaned["consumer_secret"]
        self.shortcode = cleaned["shortcode"]
        self.passkey = cleaned["passkey"]
        self.environment = cleaned["environment"]
        self.transaction_type = cleaned["transaction_type"]
        self.account_reference = cleaned["account_reference"]
        self.transaction_desc = cleaned["transaction_desc"]
        self.callback_url = callback_url
        self.base_url = (
            "https://sandbox.safaricom.co.ke"
            if self.environment == "sandbox"
            else "https://api.safaricom.co.ke"
        )

    async def _access_token(self) -> str:
        credentials = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                    headers={"Authorization": f"Basic {credentials}"},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MpesaProviderError("M-Pesa authorization request failed") from exc
        token = payload.get("access_token")
        if not token:
            raise MpesaProviderError("M-Pesa authorization did not return an access token")
        return str(token)

    async def stk_push(
        self,
        amount_minor: int,
        phone: str,
        account_reference: str | None = None,
    ) -> dict[str, str | None]:
        msisdn = mpesa_msisdn(phone)
        amount = amount_kes_from_minor(amount_minor)
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        reference = (account_reference or self.account_reference).strip()[:12]
        if not reference:
            reference = settings.app_name[:12]
        body = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": self.transaction_type,
            "Amount": amount,
            "PartyA": msisdn,
            "PartyB": self.shortcode,
            "PhoneNumber": msisdn,
            "CallBackURL": self.callback_url,
            "AccountReference": reference,
            "TransactionDesc": self.transaction_desc[:13],
        }
        token = await self._access_token()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                    json=body,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MpesaProviderError("M-Pesa payment request failed") from exc
        response_code = str(payload.get("ResponseCode", ""))
        if response_code != "0":
            raise MpesaProviderError(
                str(
                    payload.get("ResponseDescription")
                    or payload.get("errorMessage")
                    or "M-Pesa rejected the payment request"
                )
            )
        checkout_request_id = payload.get("CheckoutRequestID")
        if not checkout_request_id:
            raise MpesaProviderError("M-Pesa did not return a CheckoutRequestID")
        return {
            "merchant_request_id": str(payload.get("MerchantRequestID")) if payload.get("MerchantRequestID") else None,
            "checkout_request_id": str(checkout_request_id),
            "response_code": response_code,
            "response_message": str(
                payload.get("CustomerMessage") or payload.get("ResponseDescription") or "Payment request sent"
            ),
        }

    async def stk_query(self, checkout_request_id: str) -> dict[str, str | None]:
        """Query STK status for reconciliation when callbacks are delayed or missed."""
        if not checkout_request_id or not checkout_request_id.strip():
            raise HTTPException(status_code=422, detail="CheckoutRequestID is required")
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        body = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id.strip(),
        }
        token = await self._access_token()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}/mpesa/stkpushquery/v1/query",
                    json=body,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MpesaProviderError("M-Pesa STK query failed") from exc
        return {
            "response_code": str(payload.get("ResponseCode", "")) if payload.get("ResponseCode") is not None else None,
            "result_code": str(payload.get("ResultCode", "")) if payload.get("ResultCode") is not None else None,
            "result_desc": str(payload.get("ResultDesc") or payload.get("ResponseDescription") or "") or None,
            "merchant_request_id": str(payload.get("MerchantRequestID")) if payload.get("MerchantRequestID") else None,
            "checkout_request_id": str(payload.get("CheckoutRequestID")) if payload.get("CheckoutRequestID") else None,
        }
