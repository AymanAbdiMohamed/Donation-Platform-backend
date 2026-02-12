"""
Payment Service.

Handles M-Pesa Daraja API payment processing for donations using the new MpesaClient.

This service provides a high-level interface for donation payments and integrates
with the improved M-Pesa utility module for better error handling and logging.
"""
import logging
import os
from base64 import b64encode
from datetime import datetime
import requests
from flask import current_app

logger = logging.getLogger(__name__)


class MpesaError(Exception):
    pass


class MpesaClient:
    """Client for Safaricom Daraja API (sandbox and production)."""

    def __init__(self):
        self.consumer_key = os.environ.get("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET")
        self.shortcode = os.environ.get("MPESA_SHORTCODE")
        self.passkey = os.environ.get("MPESA_PASSKEY")
        self.callback_url = os.environ.get("MPESA_STK_CALLBACK_URL")
        self.env = os.environ.get("MPESA_ENV", "sandbox").lower()

        if not all([self.consumer_key, self.consumer_secret, self.shortcode, self.passkey, self.callback_url]):
            raise MpesaError("Incomplete M-Pesa configuration")

    def get_base_url(self) -> str:
        return "https://sandbox.safaricom.co.ke" if self.env == "sandbox" else "https://api.safaricom.co.ke"

    def get_access_token(self) -> str:
        """Fetch a valid OAuth token from Safaricom."""
        url = f"{self.get_base_url()}/oauth/v1/generate?grant_type=client_credentials"
        try:
            resp = requests.get(url, auth=(self.consumer_key, self.consumer_secret), timeout=15)
            resp.raise_for_status()
            data = resp.json()
            token = data.get("access_token")
            if not token:
                raise MpesaError(f"No access token returned: {data}")
            return token
        except requests.RequestException as exc:
            raise MpesaError(f"OAuth token request failed: {exc}")

    def generate_password(self) -> tuple[str, str]:
        """Generate STK Push password and timestamp."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        raw = f"{self.shortcode}{self.passkey}{timestamp}"
        password = b64encode(raw.encode()).decode()
        return password, timestamp

    def initiate_stk_push(self, phone: str, amount: int, reference: str, description: str) -> dict:
        """Perform STK Push request."""
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()

        # Normalize phone to 254XXXXXXXXX
        phone = str(phone).strip()
        if phone.startswith("0"):
            phone = "254" + phone[1:]
        elif phone.startswith("+"):
            phone = phone[1:]

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": str(reference)[:12],
            "TransactionDesc": str(description)[:13],
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.get_base_url()}/mpesa/stkpush/v1/processrequest"

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as exc:
            raise MpesaError(f"STK Push request failed: {exc}")

        if result.get("ResponseCode") == "0":
            return {
                "success": True,
                "checkout_request_id": result.get("CheckoutRequestID"),
                "merchant_request_id": result.get("MerchantRequestID"),
                "response_description": result.get("ResponseDescription", ""),
                "customer_message": result.get("CustomerMessage", ""),
            }

        raise MpesaError(result.get("errorMessage") or result.get("ResponseDescription") or "STK Push failed")


class PaymentService:
    """Service class for M-Pesa Daraja payment processing."""

    @staticmethod
    def is_configured() -> bool:
        try:
            MpesaClient()
            return True
        except MpesaError as e:
            logger.warning(f"M-Pesa not configured: {e}")
            return False

    @staticmethod
    def get_mpesa_access_token() -> str:
        try:
            client = MpesaClient()
            return client.get_access_token()
        except MpesaError as e:
            logger.error(f"Failed to get M-Pesa token: {e}")
            raise RuntimeError(str(e))

    @staticmethod
    def initiate_stk_push(amount: int, phone_number: str, account_reference: str, transaction_desc: str) -> dict:
        if not PaymentService.is_configured():
            return {"success": False, "error": "M-Pesa is not configured on this server"}
        try:
            client = MpesaClient()
            return client.initiate_stk_push(
                phone=phone_number,
                amount=int(amount),
                reference=account_reference,
                description=transaction_desc
            )
        except MpesaError as e:
            logger.error(f"STK Push failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in STK Push: {e}")
            return {"success": False, "error": "Payment service temporarily unavailable"}

    @staticmethod
    def parse_stk_callback(callback_data: dict) -> dict:
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
            items = body.get("CallbackMetadata", {}).get("Item", [])
            meta = {item.get("Name"): item.get("Value") for item in items}

            return {
                **base,
                "success": True,
                "mpesa_receipt_number": meta.get("MpesaReceiptNumber"),
                "amount": meta.get("Amount"),
                "phone_number": str(meta.get("PhoneNumber", "")),
                "transaction_date": str(meta.get("TransactionDate", "")),
            }

        return {**base, "success": False, "error": result_desc or "Payment was not completed"}

    @staticmethod
    def test_connection() -> dict:
        """Test connection by fetching a token."""
        try:
            token = MpesaClient().get_access_token()
            return {"success": True, "access_token": token}
        except MpesaError as e:
            return {"success": False, "error": str(e)}
