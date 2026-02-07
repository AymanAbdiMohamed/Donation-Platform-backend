"""
Payment Service.

Handles M-Pesa Daraja API payment processing for donations.
"""
import requests
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth


class PaymentService:
    """Service class for M-Pesa Daraja payment processing."""
    
    # ==========================================
    # ADD YOUR M-PESA DARAJA CREDENTIALS HERE
    # ==========================================
    CONSUMER_KEY = "YOUR_CONSUMER_KEY_HERE"
    CONSUMER_SECRET = "YOUR_CONSUMER_SECRET_HERE"
    BUSINESS_SHORT_CODE = "YOUR_BUSINESS_SHORT_CODE_HERE"
    PASSKEY = "YOUR_PASSKEY_HERE"
    
    # M-Pesa API URLs (Use sandbox for testing, production for live)
    # Sandbox URLs
    AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    STK_PUSH_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    # Production URLs (uncomment when going live)
    # AUTH_URL = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    # STK_PUSH_URL = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    CALLBACK_URL = "YOUR_CALLBACK_URL_HERE"  # e.g., "https://yourdomain.com/api/payment/callback"
    # ==========================================
    
    @staticmethod
    def get_access_token():
        """
        Get M-Pesa access token.
        
        Returns:
            str: Access token or None if failed
        """
        try:
            response = requests.get(
                PaymentService.AUTH_URL,
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
                PaymentService.STK_PUSH_URL,
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
