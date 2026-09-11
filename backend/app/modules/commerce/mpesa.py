from __future__ import annotations

import base64
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException

from app.modules.commerce.notifications import normalize_phone


class MpesaProviderError(RuntimeError):
    pass


class MpesaClient:
    def __init__(self, config: dict[str, str], callback_url: str) -> None:
        self.consumer_key = config.get("consumer_key", "")
        self.consumer_secret = config.get("consumer_secret", "")
        self.shortcode = config.get("shortcode", "")
        self.passkey = config.get("passkey", "")
        self.environment = config.get("environment", "sandbox")
        self.transaction_type = config.get("transaction_type", "CustomerPayBillOnline")
        self.account_reference = config.get("account_reference", "DukaMe Order")
        self.transaction_desc = config.get("transaction_desc", "DukaMe order payment")
        self.callback_url = callback_url
        if not all((self.consumer_key, self.consumer_secret, self.shortcode, self.passkey, callback_url)):
            raise HTTPException(status_code=503, detail="M-Pesa payment configuration is incomplete")
        if self.environment not in {"sandbox", "production"}:
            raise HTTPException(status_code=503, detail="M-Pesa environment is invalid")
        self.base_url = "https://sandbox.safaricom.co.ke" if self.environment == "sandbox" else "https://api.safaricom.co.ke"

    async def _access_token(self) -> str:
        credentials = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials", headers={"Authorization": f"Basic {credentials}"})
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MpesaProviderError("M-Pesa authorization request failed") from exc
        token = payload.get("access_token")
        if not token:
            raise MpesaProviderError("M-Pesa authorization did not return an access token")
        return str(token)

    async def stk_push(self, amount_minor: int, phone: str, account_reference: str | None = None) -> dict[str, str | None]:
        normalized_phone = normalize_phone(phone)
        if not normalized_phone.startswith("+") or len(normalized_phone) < 13:
            raise HTTPException(status_code=422, detail="Enter a valid Kenyan M-Pesa phone number")
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        body = {"BusinessShortCode": self.shortcode, "Password": password, "Timestamp": timestamp, "TransactionType": self.transaction_type, "Amount": max(1, round(amount_minor / 100)), "PartyA": normalized_phone[1:], "PartyB": self.shortcode, "PhoneNumber": normalized_phone[1:], "CallBackURL": self.callback_url, "AccountReference": (account_reference or self.account_reference)[:12], "TransactionDesc": self.transaction_desc[:13]}
        token = await self._access_token()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(f"{self.base_url}/mpesa/stkpush/v1/processrequest", json=body, headers={"Authorization": f"Bearer {token}"})
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MpesaProviderError("M-Pesa payment request failed") from exc
        response_code = str(payload.get("ResponseCode", ""))
        if response_code != "0":
            raise MpesaProviderError(str(payload.get("ResponseDescription") or payload.get("errorMessage") or "M-Pesa rejected the payment request"))
        return {"merchant_request_id": str(payload.get("MerchantRequestID")) if payload.get("MerchantRequestID") else None, "checkout_request_id": str(payload.get("CheckoutRequestID")) if payload.get("CheckoutRequestID") else None, "response_code": response_code, "response_message": str(payload.get("CustomerMessage") or payload.get("ResponseDescription") or "Payment request sent")}
