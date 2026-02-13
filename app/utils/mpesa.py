"""
M-Pesa Daraja API Helper Module.

Production-ready helper functions for M-Pesa integration with proper error handling,
logging, and token management. This module provides a clean interface for:
- OAuth token generation and caching
- STK Push initiation 
- Payment status checking
- Callback validation

Usage:
    from app.utils.mpesa import MpesaClient
    
    client = MpesaClient()
    token = client.get_access_token()
    result = client.initiate_stk_push(phone="254712345678", amount=100, reference="DONATION")
"""
import os
import time
import base64
import logging
import random
from datetime import datetime
from typing import Dict, Tuple, Optional

import requests
from requests.auth import HTTPBasicAuth
from flask import current_app

logger = logging.getLogger(__name__)

# Token cache - shared across all instances
_token_cache = {
    "access_token": None,
    "expires_at": 0,
}


class MpesaError(Exception):
    """Custom exception for M-Pesa API errors."""
    pass


class MpesaClient:
    """
    M-Pesa Daraja API client with production-ready error handling and logging.
    
    Features:
    - Automatic token caching and refresh
    - Comprehensive error handling
    - Request/response logging
    - Environment-aware endpoints (sandbox/production)
    """
    
    def __init__(self):
        """Initialize client with configuration from Flask app."""
        self.env = current_app.config.get("MPESA_ENV", "sandbox")
        self.base_url = self._get_base_url()
        print(f"DEBUG: MpesaClient initialized. Context: {current_app.name}")
        print(f"DEBUG: MPESA_MOCK_MODE from config: {current_app.config.get('MPESA_MOCK_MODE')}")
        print(f"DEBUG: MPESA_MOCK_MODE from environ: {os.environ.get('MPESA_MOCK_MODE')}")
        self._validate_config()
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL based on environment."""
        if self.env == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"
    
    def _validate_config(self) -> None:
        """Validate that all required M-Pesa configuration is present."""
        # Mock mode check
        config_mock = str(self._get_config("MPESA_MOCK_MODE")).lower()
        env_mock = str(os.environ.get("MPESA_MOCK_MODE", "")).lower()
        is_mock = config_mock == "true" or env_mock == "true"
        
        if is_mock:
            logger.info("⚠️ M-Pesa Mock Mode enabled: Skipping configuration validation")
            return
    

        required_keys = [
            "MPESA_CONSUMER_KEY",
            "MPESA_CONSUMER_SECRET", 
            "MPESA_SHORTCODE",
            "MPESA_PASSKEY",
            "MPESA_STK_CALLBACK_URL"
        ]
        
        missing = []
        for key in required_keys:
            if not current_app.config.get(key):
                missing.append(key)
        
        if missing:
            raise MpesaError(f"Missing M-Pesa configuration: {', '.join(missing)}")
        
        logger.info(f"M-Pesa client initialized for {self.env} environment")
    
    def _get_config(self, key: str) -> str:
        """Get configuration value from Flask app."""
        return current_app.config.get(key, "")
    
    def get_access_token(self) -> str:
        """
        Get a valid M-Pesa OAuth access token.
        
        Automatically caches tokens and refreshes them 60 seconds before expiry
        to avoid race conditions.
        
        Returns:
            str: Valid Bearer token
            
        Raises:
            MpesaError: If token generation fails
        """
        now = time.time()
        
        if (_token_cache["access_token"] and 
            _token_cache["expires_at"] - 60 > now):
            logger.debug("Using cached M-Pesa token")
            return _token_cache["access_token"]
            
        config_mock = str(self._get_config("MPESA_MOCK_MODE")).lower()
        env_mock = str(os.environ.get("MPESA_MOCK_MODE", "")).lower()
        
        if config_mock == "true" or env_mock == "true":
            return "mock_access_token_12345"
        
        logger.info("Refreshing M-Pesa access token...")
        
        logger.info("Refreshing M-Pesa access token...")
        
        consumer_key = self._get_config("MPESA_CONSUMER_KEY")
        consumer_secret = self._get_config("MPESA_CONSUMER_SECRET")
        
        if not consumer_key or not consumer_secret:
            raise MpesaError("MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET must be configured")
        
        # Prepare OAuth request
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        # Create proper Basic auth header
        auth_string = f"{consumer_key}:{consumer_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
        }
        
        try:
            logger.debug(f"Requesting token from: {url}")
            logger.debug(f"Using consumer key: {consumer_key[:8]}...")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            # Log response for debugging
            logger.debug(f"Token response status: {response.status_code}")
            logger.debug(f"Token response headers: {response.headers}")
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Token request failed: {response.status_code} - {error_text}")
                raise MpesaError(f"OAuth failed: {response.status_code} - {error_text}")
            
            data = response.json()
            logger.debug(f"Token response: {data}")
            
        except requests.RequestException as e:
            logger.error(f"Token request network error: {e}")
            raise MpesaError(f"Network error during token request: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON in token response: {e}")
            raise MpesaError(f"Invalid response format: {e}")
        
        # Extract token and expiry
        access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))
        
        if not access_token:
            logger.error(f"No access token in response: {data}")
            raise MpesaError("No access_token in OAuth response")
        
        # Cache the token
        _token_cache["access_token"] = access_token
        _token_cache["expires_at"] = now + expires_in
        
        logger.info(f"M-Pesa token refreshed successfully (expires in {expires_in}s)")
        return access_token
    
    def generate_password(self) -> Tuple[str, str]:
        """
        Generate STK Push password and timestamp.
        
        Returns:
            Tuple[str, str]: (base64_password, timestamp)
        """
        shortcode = self._get_config("MPESA_SHORTCODE")
        passkey = self._get_config("MPESA_PASSKEY")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Create password: shortcode + passkey + timestamp
        password_string = f"{shortcode}{passkey}{timestamp}"
        password_bytes = password_string.encode('utf-8')
        password_b64 = base64.b64encode(password_bytes).decode('utf-8')
        
        logger.debug(f"Generated password for timestamp: {timestamp}")
        return password_b64, timestamp
    
    def initiate_stk_push(
        self,
        phone: str,
        amount: int,
        reference: str,
        description: str = "Donation Payment"
    ) -> Dict:
        """
        Initiate an M-Pesa STK Push payment.
        
        Args:
            phone: Customer phone in 254XXXXXXXXX format
            amount: Amount in KES (whole number)
            reference: Account reference (max 12 chars)
            description: Transaction description (max 13 chars)
            
        Returns:
            Dict with success, checkout_request_id, etc.
            
        Raises:
            MpesaError: If STK push fails
        """
        logger.info(f"Initiating STK Push: {amount} KES to {phone}")
        
        # Check for Mock Mode
        config_mock = str(self._get_config("MPESA_MOCK_MODE")).lower()
        env_mock = str(os.environ.get("MPESA_MOCK_MODE", "")).lower()
        
        if config_mock == "true" or env_mock == "true":
            logger.info("⚠️ M-Pesa Mock Mode Enabled: Simulating STK Push with realistic delay")
            
            checkout_id = f"ws_CO_{int(time.time())}{random.randint(100, 999)}"
            merchant_id = f"GR_{int(time.time())}{random.randint(100, 999)}"
            
            # Start background thread to simulate callback after 30-40 seconds
            from app.utils.mock_mpesa import start_mock_callback
            from flask import current_app
            
            start_mock_callback(
                checkout_request_id=checkout_id,
                phone=phone,
                amount=amount,
                app=current_app._get_current_object()
            )
            
            return {
                "success": True,
                "checkout_request_id": checkout_id,
                "merchant_request_id": merchant_id,
                "response_description": "Success. Request accepted for processing",
                "customer_message": "Success. Request accepted for processing"
            }

        # Get fresh token
        try:
            access_token = self.get_access_token()
        except MpesaError:
            logger.error("Failed to get access token for STK Push")
            raise
        
        # Generate password and timestamp
        password, timestamp = self.generate_password()
        
        # Normalize phone number
        normalized_phone = self._normalize_phone(phone)
        if not normalized_phone:
            raise MpesaError(f"Invalid phone number format: {phone}")
        
        # Prepare STK Push payload
        shortcode = self._get_config("MPESA_SHORTCODE")
        callback_url = self._get_config("MPESA_STK_CALLBACK_URL")
        
        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": normalized_phone,
            "PartyB": shortcode,
            "PhoneNumber": normalized_phone,
            "CallBackURL": callback_url,
            "AccountReference": reference[:12],
            "TransactionDesc": description[:13]
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        try:
            logger.debug(f"STK Push URL: {url}")
            logger.debug(f"STK Push payload: {payload}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.debug(f"STK Push response status: {response.status_code}")
            logger.debug(f"STK Push response: {response.text}")
            
            if response.status_code != 200:
                raise MpesaError(f"STK Push failed: {response.status_code} - {response.text}")
            
            result = response.json()
            
        except requests.RequestException as e:
            logger.error(f"STK Push network error: {e}")
            raise MpesaError(f"Network error during STK Push: {e}")
        except ValueError as e:
            logger.error(f"Invalid JSON in STK Push response: {e}")
            raise MpesaError(f"Invalid response format: {e}")
        
        # Check if request was successful
        response_code = result.get("ResponseCode")
        if response_code == "0":
            checkout_id = result.get("CheckoutRequestID")
            logger.info(f"STK Push successful: {checkout_id}")
            
            return {
                "success": True,
                "checkout_request_id": checkout_id,
                "merchant_request_id": result.get("MerchantRequestID"),
                "response_description": result.get("ResponseDescription", ""),
                "customer_message": result.get("CustomerMessage", "")
            }
        else:
            error_msg = result.get("ResponseDescription") or result.get("errorMessage") or "Unknown error"
            logger.error(f"STK Push failed: {response_code} - {error_msg}")
            
            return {
                "success": False,
                "error": error_msg, # Changed from str(e) to error_msg to match original logic
                "checkout_request_id": None # Added this line
            }
    
    def query_stk_status(self, checkout_request_id: str) -> Dict:
        """
        Query the status of an STK Push transaction.
        
        Args:
            checkout_request_id: The CheckoutRequestID from STK Push response
            
        Returns:
            Dict with status information
        """
        logger.info(f"Querying STK Push status for: {checkout_request_id}")
        
        # Check for Mock Mode
        config_mock = str(self._get_config("MPESA_MOCK_MODE")).lower()
        env_mock = str(os.environ.get("MPESA_MOCK_MODE", "")).lower()
        
        if config_mock == "true" or env_mock == "true":
            logger.info("⚠️ M-Pesa Mock Mode: Simulating successful query")
            return {
                "success": True,
                "result_code": "0",
                "result_desc": "The service request is processed successfully.",
                "checkout_request_id": checkout_request_id
            }
        
        # Get fresh token
        try:
            access_token = self.get_access_token()
        except Exception as e:
            logger.error(f"Failed to get access token for query: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }
        
        # Generate password and timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        shortcode = self._get_config("MPESA_SHORTCODE")
        passkey = self._get_config("MPESA_PASSKEY")
        password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()
        
        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        try:
            logger.debug(f"STK Query URL: {url}")
            logger.debug(f"STK Query payload: {payload}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logger.debug(f"STK Query response status: {response.status_code}")
            logger.debug(f"STK Query response: {response.text}")
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Query failed: {response.status_code} - {response.text}"
                }
            
            data = response.json()
            
            # Check ResponseCode first
            if data.get("ResponseCode") != "0":
                return {
                    "success": False,
                    "error": data.get("ResponseDescription", "Query request failed")
                }
            
            # Return the result
            result_code = data.get("ResultCode")
            result_desc = data.get("ResultDesc", "")
            
            return {
                "success": True,
                "result_code": result_code,
                "result_desc": result_desc,
                "checkout_request_id": data.get("CheckoutRequestID"),
                "merchant_request_id": data.get("MerchantRequestID"),
                "is_complete": result_code is not None,
                "is_successful": result_code == "0"
            }
            
        except Exception as e:
            logger.error(f"STK Query error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _normalize_phone(self, phone: str) -> Optional[str]:
        """
        Normalize phone number to 254XXXXXXXXX format.
        
        Args:
            phone: Input phone number
            
        Returns:
            Normalized phone or None if invalid
        """
        if not phone:
            return None
        
        # Clean the phone number
        clean = str(phone).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Handle different formats
        if clean.startswith("+254"):
            clean = clean[1:]  # Remove +
        elif clean.startswith("0"):
            clean = "254" + clean[1:]  # Replace 0 with 254
        elif clean.startswith("254"):
            pass  # Already correct
        else:
            return None
        
        # Validate final format
        if len(clean) == 12 and clean.startswith("254") and clean[3:].isdigit():
            return clean
        
        return None
    
    @staticmethod
    def parse_callback(callback_data: Dict) -> Dict:
        """
        Parse M-Pesa callback data.
        
        Args:
            callback_data: Raw callback payload from Safaricom
            
        Returns:
            Dict with parsed callback information
        """
        try:
            stk_callback = callback_data.get("Body", {}).get("stkCallback", {})
        except (AttributeError, TypeError):
            return {"success": False, "error": "Invalid callback format"}
        
        result_code = stk_callback.get("ResultCode")
        checkout_id = stk_callback.get("CheckoutRequestID")
        result_desc = stk_callback.get("ResultDesc", "")
        
        base_result = {
            "checkout_request_id": checkout_id,
            "merchant_request_id": stk_callback.get("MerchantRequestID"),
            "result_code": result_code,
            "result_desc": result_desc
        }
        
        if result_code == 0:
            # Payment successful - extract metadata
            metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            meta_dict = {}
            
            for item in metadata:
                key = item.get("Name")
                value = item.get("Value")
                if key and value is not None:
                    meta_dict[key] = value
            
            return {
                **base_result,
                "success": True,
                "mpesa_receipt_number": meta_dict.get("MpesaReceiptNumber"),
                "amount": meta_dict.get("Amount"),
                "phone_number": str(meta_dict.get("PhoneNumber", "")),
                "transaction_date": str(meta_dict.get("TransactionDate", ""))
            }
        else:
            # Payment failed or cancelled
            return {
                **base_result,
                "success": False,
                "error": result_desc or "Payment not completed"
            }


def test_mpesa_connection() -> Dict:
    """
    Test M-Pesa connection and credentials.
    
    Returns:
        Dict with test results
    """
    try:
        client = MpesaClient()
        token = client.get_access_token()
        
        return {
            "success": True,
            "message": "M-Pesa connection successful",
            "token_preview": token[:20] + "..." if token else None,
            "environment": client.env
        }
    except Exception as e:
        logger.error(f"M-Pesa connection test failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def validate_phone_number(phone: str) -> bool:
    """
    Validate Kenyan phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        bool: True if valid Kenyan phone number
    """
    client = MpesaClient()
    normalized = client._normalize_phone(phone)
    return normalized is not None