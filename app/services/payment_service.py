"""
Payment Service.

Handles M-Pesa Daraja API payment processing for donations.

All credentials are read from Flask app.config (populated from environment
variables via config.py).  The service never reads os.environ directly.

Token caching: The OAuth access token is cached in-memory with its expiry
time and refreshed automatically when it expires.
"""
import time
import base64
import logging
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth
from flask import current_app

logger = logging.getLogger(__name__)

# ── In-memory token cache ───────────────────────────────────────────────────
_token_cache = {
    "access_token": None,
    "expires_at": 0,  # epoch seconds
}

# ── Daraja API base URLs ────────────────────────────────────────────────────
_SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
_PRODUCTION_BASE = "https://api.safaricom.co.ke"


def _base_url():
    """Return the correct API base URL based on MPESA_ENV."""
    env = current_app.config.get("MPESA_ENV", "sandbox")
    return _PRODUCTION_BASE if env == "production" else _SANDBOX_BASE


class PaymentService:
    """Service class for M-Pesa Daraja payment processing."""

    # ── Configuration helpers (read from Flask config at runtime) ────────

    @staticmethod
    def _cfg(key):
        """Read an MPESA_* config value from the running Flask app."""
        return current_app.config.get(key, "")

    @staticmethod
    def is_configured():
        """Return True if all required M-Pesa credentials are present."""
        required = [
            "MPESA_CONSUMER_KEY",
            "MPESA_CONSUMER_SECRET",
            "MPESA_SHORTCODE",
            "MPESA_PASSKEY",
            "MPESA_STK_CALLBACK_URL",
        ]
        missing = [k for k in required if not current_app.config.get(k)]
        if missing:
            logger.warning("M-Pesa not configured — missing: %s", ", ".join(missing))
            return False
        return True

    # ── OAuth Token ─────────────────────────────────────────────────────

    @staticmethod
    def get_mpesa_access_token():
        """
        Get a valid M-Pesa OAuth access token.

        Caches the token in-memory and automatically refreshes it 60 s
        before the advertised expiry.

        Returns:
            str: Bearer access token.

        Raises:
            RuntimeError: If the token request fails.
        """
        now = time.time()

        # Return cached token if still valid (with 60 s buffer)
        if _token_cache["access_token"] and _token_cache["expires_at"] - 60 > now:
            return _token_cache["access_token"]

        consumer_key = PaymentService._cfg("MPESA_CONSUMER_KEY")
        consumer_secret = PaymentService._cfg("MPESA_CONSUMER_SECRET")

        if not consumer_key or not consumer_secret:
            raise RuntimeError(
                "MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET must be set"
            )

        url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"

        try:
            resp = requests.get(
                url,
                auth=HTTPBasicAuth(consumer_key, consumer_secret),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("Daraja OAuth request failed: %s", exc)
            raise RuntimeError(f"Failed to obtain M-Pesa access token: {exc}") from exc

        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3599))  # seconds

        if not token:
            raise RuntimeError("Daraja response did not contain an access_token")

        _token_cache["access_token"] = token
        _token_cache["expires_at"] = now + expires_in

        logger.info("M-Pesa access token refreshed (expires in %d s)", expires_in)
        return token

    # ── Password / timestamp generation ─────────────────────────────────

    @staticmethod
    def generate_password():
        """
        Generate the STK Push password.

        Returns:
            tuple[str, str]: (base64-encoded password, timestamp)
        """
        shortcode = PaymentService._cfg("MPESA_SHORTCODE")
        passkey = PaymentService._cfg("MPESA_PASSKEY")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        raw = f"{shortcode}{passkey}{timestamp}"
        password = base64.b64encode(raw.encode()).decode("utf-8")
        return password, timestamp

    # ── STK Push ────────────────────────────────────────────────────────

    @staticmethod
    def initiate_stk_push(amount, phone_number, account_reference, transaction_desc):
        """
        Initiate an M-Pesa STK Push (Lipa Na M-Pesa Online).

        Args:
            amount: Amount in KES (integer).
            phone_number: Customer phone in 254XXXXXXXXX format.
            account_reference: e.g. charity name or "DONATION-<id>".
            transaction_desc: Human-readable description.

        Returns:
            dict with keys:
                success (bool)
                checkout_request_id (str)
                merchant_request_id (str)
                response_description (str)
                customer_message (str)
            On failure the dict has ``success=False`` and an ``error`` key.
        """
        if not PaymentService.is_configured():
            return {"success": False, "error": "M-Pesa is not configured on this server"}

        try:
            access_token = PaymentService.get_mpesa_access_token()
        except RuntimeError as exc:
            return {"success": False, "error": str(exc)}

        password, timestamp = PaymentService.generate_password()
        shortcode = PaymentService._cfg("MPESA_SHORTCODE")
        callback_url = PaymentService._cfg("MPESA_STK_CALLBACK_URL")

        # Normalise phone number to 254XXXXXXXXX
        phone_number = str(phone_number).strip()
        if phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        elif phone_number.startswith("+"):
            phone_number = phone_number[1:]

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": str(account_reference)[:12],  # max 12 chars
            "TransactionDesc": str(transaction_desc)[:13],    # max 13 chars
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as exc:
            logger.error("STK Push request failed: %s", exc)
            return {"success": False, "error": f"STK Push request failed: {exc}"}

        if result.get("ResponseCode") == "0":
            return {
                "success": True,
                "checkout_request_id": result.get("CheckoutRequestID"),
                "merchant_request_id": result.get("MerchantRequestID"),
                "response_description": result.get("ResponseDescription", ""),
                "customer_message": result.get("CustomerMessage", ""),
            }

        return {
            "success": False,
            "error": result.get("ResponseDescription")
                     or result.get("errorMessage")
                     or "STK Push initiation failed",
        }

    # ── Callback parsing ────────────────────────────────────────────────

    @staticmethod
    def parse_stk_callback(callback_data):
        """
        Parse the M-Pesa STK callback payload.

        Returns:
            dict with keys:
                success (bool)
                checkout_request_id (str)
                merchant_request_id (str)
                result_code (int)
                result_desc (str)
                mpesa_receipt_number (str | None)  — only on success
                amount (int | None)
                phone_number (str | None)
                transaction_date (str | None)
        """
        try:
            body = callback_data.get("Body", {}).get("stkCallback", {})
        except (AttributeError, TypeError):
            return {"success": False, "error": "Malformed callback payload"}

        result_code = body.get("ResultCode")
        checkout_id = body.get("CheckoutRequestID")
        merchant_id = body.get("MerchantRequestID")
        result_desc = body.get("ResultDesc", "")

        base = {
            "checkout_request_id": checkout_id,
            "merchant_request_id": merchant_id,
            "result_code": result_code,
            "result_desc": result_desc,
        }

        if result_code == 0:
            # Payment succeeded — extract metadata
            items = body.get("CallbackMetadata", {}).get("Item", [])
            meta = {}
            for item in items:
                meta[item.get("Name")] = item.get("Value")

            return {
                **base,
                "success": True,
                "mpesa_receipt_number": meta.get("MpesaReceiptNumber"),
                "amount": meta.get("Amount"),
                "phone_number": str(meta.get("PhoneNumber", "")),
                "transaction_date": str(meta.get("TransactionDate", "")),
            }

        # Payment failed / cancelled
        return {
            **base,
            "success": False,
            "error": result_desc or "Payment was not completed",
        }

