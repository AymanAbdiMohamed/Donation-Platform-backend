"""
Payment Service.

Handles M-Pesa Daraja API payment processing for donations using the new MpesaClient.

This service provides a high-level interface for donation payments and integrates
with the improved M-Pesa utility module for better error handling and logging.
"""
import logging
from flask import current_app

from app.utils.mpesa import MpesaClient, MpesaError, test_mpesa_connection

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for M-Pesa Daraja payment processing."""

    @staticmethod
    def is_configured():
        """
        Check if M-Pesa is properly configured.
        
        Returns:
            bool: True if all required M-Pesa config is present
        """
        try:
            # This will validate configuration
            MpesaClient()
            return True
        except MpesaError as e:
            logger.warning(f"M-Pesa not configured: {e}")
            return False

    @staticmethod
    def get_mpesa_access_token():
        """
        Get a valid M-Pesa OAuth access token.
        
        Returns:
            str: Bearer access token
            
        Raises:
            RuntimeError: If token generation fails
        """
        try:
            client = MpesaClient()
            return client.get_access_token()
        except MpesaError as e:
            logger.error(f"Failed to get M-Pesa token: {e}")
            raise RuntimeError(str(e))

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
            client = MpesaClient()
            return client.initiate_stk_push(
                phone=phone_number,
                amount=int(amount),
                reference=str(account_reference),
                description=str(transaction_desc)
            )
        except MpesaError as e:
            logger.error(f"STK Push failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in STK Push: {e}")
            return {"success": False, "error": "Payment service temporarily unavailable"}

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
        return MpesaClient.parse_callback(callback_data)

    @staticmethod
    def test_connection():
        """
        Test M-Pesa connection and configuration.
        
        Returns:
            dict: Test results with success status and details
        """
        return test_mpesa_connection()

    # Legacy methods for backward compatibility
    @staticmethod
    def generate_password():
        """Generate STK Push password (legacy method)."""
        try:
            client = MpesaClient()
            return client.generate_password()
        except MpesaError as e:
            raise RuntimeError(str(e))

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
                mpesa_receipt_number (str | None)  # only on success
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

