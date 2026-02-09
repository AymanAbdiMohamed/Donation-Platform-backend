"""
Payment Service.

Handles M-Pesa Daraja API payment processing for donations.

Required environment variables (all optional in dev — the service will report
itself as unconfigured when any are missing):
    MPESA_CONSUMER_KEY
    MPESA_CONSUMER_SECRET
    MPESA_SHORTCODE
    MPESA_PASSKEY
    MPESA_CALLBACK_URL
    MPESA_ENVIRONMENT    – "sandbox" (default) or "production"
"""
import os
import requests
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth


class PaymentService:
    """Service class for M-Pesa Daraja payment processing."""

    # ── Credentials from environment variables ──────────────────────
    CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
    CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
    BUSINESS_SHORT_CODE = os.environ.get("MPESA_SHORTCODE", "")
    PASSKEY = os.environ.get("MPESA_PASSKEY", "")
    CALLBACK_URL = os.environ.get("MPESA_CALLBACK_URL", "")

    # ── API URLs ────────────────────────────────────────────────────
    _SANDBOX_AUTH = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    _SANDBOX_STK = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    _PROD_AUTH = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    _PROD_STK = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    @classmethod
    def _is_production(cls):
        return os.environ.get("MPESA_ENVIRONMENT", "sandbox").lower() == "production"

    @classmethod
    def _auth_url(cls):
        return cls._PROD_AUTH if cls._is_production() else cls._SANDBOX_AUTH

    @classmethod
    def _stk_url(cls):
        return cls._PROD_STK if cls._is_production() else cls._SANDBOX_STK

    @classmethod
    def is_configured(cls):
        """Return True if all required M-Pesa credentials are set."""
        return all([
            cls.CONSUMER_KEY,
            cls.CONSUMER_SECRET,
            cls.BUSINESS_SHORT_CODE,
            cls.PASSKEY,
            cls.CALLBACK_URL,
        ])
    
    @staticmethod
    def get_access_token():
        """
        Get M-Pesa access token.
        
        Returns:
            str: Access token or None if failed
        """
        if not PaymentService.is_configured():
            print("M-Pesa is not configured — set MPESA_* environment variables")
            return None

        try:
            response = requests.get(
                PaymentService._auth_url(),
                auth=HTTPBasicAuth(PaymentService.CONSUMER_KEY, PaymentService.CONSUMER_SECRET)
            )
            response.raise_for_status()
            return response.json().get("access_token")
        except Exception as e:
            print(f"Error getting access token: {str(e)}")
            return None
    
    @staticmethod
    def generate_password():
        """
        Generate M-Pesa password.
        
        Returns:
            tuple: (password, timestamp)
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        data_to_encode = f"{PaymentService.BUSINESS_SHORT_CODE}{PaymentService.PASSKEY}{timestamp}"
        password = base64.b64encode(data_to_encode.encode()).decode("utf-8")
        return password, timestamp
    
    @staticmethod
    def create_payment_intent(amount, phone_number, account_reference, transaction_desc):
        """
        Initiate M-Pesa STK Push payment.
        
        Args:
            amount: Payment amount in KES (will be converted to integer)
            phone_number: Customer phone number (format: 254XXXXXXXXX)
            account_reference: Account reference (e.g., donation ID)
            transaction_desc: Transaction description
            
        Returns:
            dict: Payment intent result with checkout_request_id and response_code
        """
        access_token = PaymentService.get_access_token()
        if not access_token:
            return {
                "success": False,
                "error": "Failed to get access token"
            }
        
        password, timestamp = PaymentService.generate_password()
        
        # Ensure phone number is in correct format
        if phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        elif phone_number.startswith("+"):
            phone_number = phone_number[1:]
        
        payload = {
            "BusinessShortCode": PaymentService.BUSINESS_SHORT_CODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": PaymentService.BUSINESS_SHORT_CODE,
            "PhoneNumber": phone_number,
            "CallBackURL": PaymentService.CALLBACK_URL,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                PaymentService._stk_url(),
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("ResponseCode") == "0":
                return {
                    "success": True,
                    "checkout_request_id": result.get("CheckoutRequestID"),
                    "merchant_request_id": result.get("MerchantRequestID"),
                    "response_code": result.get("ResponseCode"),
                    "response_description": result.get("ResponseDescription"),
                    "customer_message": result.get("CustomerMessage")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("ResponseDescription", "Payment initiation failed")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Payment request failed: {str(e)}"
            }
    
    @staticmethod
    def confirm_payment(callback_data):
        """
        Process M-Pesa callback and confirm payment.
        
        Args:
            callback_data: Callback data from M-Pesa
            
        Returns:
            dict: Confirmation result with transaction details
        """
        try:
            body = callback_data.get("Body", {}).get("stkCallback", {})
            result_code = body.get("ResultCode")
            
            if result_code == 0:
                # Payment successful
                callback_metadata = body.get("CallbackMetadata", {}).get("Item", [])
                
                # Extract transaction details
                transaction_details = {}
                for item in callback_metadata:
                    name = item.get("Name")
                    value = item.get("Value")
                    transaction_details[name] = value
                
                return {
                    "success": True,
                    "transaction_id": transaction_details.get("MpesaReceiptNumber"),
                    "amount": transaction_details.get("Amount"),
                    "phone_number": transaction_details.get("PhoneNumber"),
                    "transaction_date": transaction_details.get("TransactionDate"),
                    "checkout_request_id": body.get("CheckoutRequestID"),
                    "merchant_request_id": body.get("MerchantRequestID")
                }
            else:
                # Payment failed
                return {
                    "success": False,
                    "error": body.get("ResultDesc", "Payment failed"),
                    "result_code": result_code
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing callback: {str(e)}"
            }
    
    @staticmethod
    def get_transaction_reference(checkout_request_id):
        """
        Get transaction reference from checkout request ID.
        
        Args:
            checkout_request_id: Checkout request ID from STK push
            
        Returns:
            str: Transaction reference
        """
        return f"MPESA-{checkout_request_id}"
