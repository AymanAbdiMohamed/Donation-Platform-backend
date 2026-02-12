"""
Payment Service.

Handles M-Pesa Daraja API payment processing for donations using the new MpesaClient.

This service provides a high-level interface for donation payments and integrates
with the improved M-Pesa utility module for better error handling and logging.
"""
import logging
from flask import current_app

import requests

from app.utils.mpesa import MpesaClient, MpesaError, test_mpesa_connection

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for M-Pesa Daraja payment processing."""

    @staticmethod
    def is_configured() -> bool:
        """
        Check if M-Pesa is properly configured.
        Returns:
            bool: True if all required M-Pesa config is present
        """
        try:
            MpesaClient()  # Validate configuration
            return True
        except MpesaError as e:
            logger.warning(f"M-Pesa not configured: {e}")
            return False

    @staticmethod
    def get_mpesa_access_token() -> str:
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
    def initiate_stk_push(amount: int, phone_number: str, account_reference: str, transaction_desc: str) -> dict:
        """
        Initiate an M-Pesa STK Push (Lipa Na M-Pesa Online).

        Args:
            amount: Amount in KES.
            phone_number: Customer phone in 254XXXXXXXXX format.
            account_reference: e.g., charity name or "DONATION-<id>".
            transaction_desc: Human-readable description.

        Returns:
            dict: success status and response details or error message
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
    def generate_password() -> tuple[str, str]:
        """
        Legacy STK Push password generation.

        Returns:
            tuple: (password, timestamp)
        Raises:
            RuntimeError: if password cannot be generated
        """
        try:
            client = MpesaClient()
            return client.generate_password()
        except MpesaError as e:
            raise RuntimeError(str(e))

    @staticmethod
    def legacy_stk_push(amount: int, phone_number: str, account_reference: str, transaction_desc: str) -> dict:
        """
        Legacy STK Push using raw HTTP request.
        """
        if not PaymentService.is_configured():
            return {"success": False, "error": "M-Pesa is not configured on this server"}

        try:
            access_token = PaymentService.get_mpesa_access_token()
            password, timestamp = PaymentService.generate_password()
        except RuntimeError as exc:
            return {"success": False, "error": str(exc)}

        shortcode = current_app.config.get("MPESA_SHORTCODE")
        callback_url = current_app.config.get("MPESA_STK_CALLBACK_URL")

        # Normalize phone number to 254XXXXXXXXX
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

        base_url = MpesaClient.get_base_url()
        url = f"{base_url}/mpesa/stkpush/v1/processrequest"

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

    @staticmethod
    def parse_stk_callback(callback_data: dict) -> dict:
        """
        Parse the M-Pesa STK callback payload.

        Args:
            callback_data: Dictionary from Safaricom callback

        Returns:
            dict: Parsed results including success, IDs, and metadata
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
            meta = {item.get("Name"): item.get("Value") for item in items}

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

    @staticmethod
    def test_connection() -> dict:
        """
        Test M-Pesa connection and configuration.

        Returns:
            dict: Test results with success status and details
        """
        return test_mpesa_connection()
