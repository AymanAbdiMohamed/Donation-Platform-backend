"""
Pesapal Payment Gateway Integration.

Handles payment initiation and callback processing for Pesapal.
"""
import hashlib
import hmac
import time
from typing import Dict, Optional
from urllib.parse import urlencode

import requests
from requests_oauthlib import OAuth1
from flask import current_app

import logging
logger = logging.getLogger(__name__)


class PesapalClient:
    """
    Pesapal payment gateway client.
    
    Handles payment initiation and IPN callback processing.
    """
    
    def __init__(self):
        """Initialize client with configuration from Flask app."""
        self.consumer_key = current_app.config.get("PESAPAL_CONSUMER_KEY")
        self.consumer_secret = current_app.config.get("PESAPAL_CONSUMER_SECRET")
        self.env = current_app.config.get("PESAPAL_ENV", "sandbox")
        self.base_url = self._get_base_url()
        
        if not self.consumer_key or not self.consumer_secret:
            raise ValueError("PESAPAL_CONSUMER_KEY and PESAPAL_CONSUMER_SECRET must be configured")
        
        logger.info(f"Pesapal client initialized for {self.env} environment")
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL based on environment."""
        if self.env == "production":
            return "https://www.pesapal.com/API"
        return "https://demo.pesapal.com/API"
    
    def initiate_payment(
        self,
        amount: float,
        description: str,
        reference: str,
        email: str,
        phone: str,
        callback_url: str
    ) -> Dict:
        """
        Initiate a payment request.
        
        Args:
            amount: Amount in KES
            description: Payment description
            reference: Unique transaction reference
            email: Customer email
            phone: Customer phone number
            callback_url: URL for payment callback
            
        Returns:
            Dict with success status and payment URL or error
        """
        logger.info(f"Initiating Pesapal payment: {amount} KES for {reference}")
        
        # Build XML request
        xml_data = f"""<?xml version="1.0" encoding="utf-8"?>
<PesapalDirectOrderInfo 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    Amount="{amount}"
    Description="{description}"
    Type="MERCHANT"
    Reference="{reference}"
    Email="{email}"
    PhoneNumber="{phone}"
    xmlns="http://www.pesapal.com" />"""
        
        # Prepare OAuth request
        url = f"{self.base_url}/PostPesapalDirectOrderV4"
        
        params = {
            "oauth_callback": callback_url,
            "pesapal_request_data": xml_data
        }
        
        try:
            # Create OAuth1 session
            auth = OAuth1(
                self.consumer_key,
                self.consumer_secret,
                signature_method='HMAC-SHA1',
                signature_type='query'
            )
            
            # Make request
            response = requests.post(
                url,
                params=params,
                auth=auth,
                timeout=30
            )
            
            logger.debug(f"Pesapal response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                # Response format: pesapal_tracking_id
                tracking_id = response.text.strip()
                
                if tracking_id:
                    payment_url = f"{self.base_url}/PostPesapalDirectOrderV4?pesapal_merchant_reference={reference}&pesapal_tracking_id={tracking_id}"
                    
                    logger.info(f"Payment initiated successfully: {tracking_id}")
                    
                    return {
                        "success": True,
                        "tracking_id": tracking_id,
                        "payment_url": payment_url,
                        "reference": reference
                    }
                else:
                    logger.error("Empty tracking ID received from Pesapal")
                    return {
                        "success": False,
                        "error": "Failed to get tracking ID from Pesapal"
                    }
            else:
                logger.error(f"Pesapal request failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Payment gateway error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Pesapal payment initiation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def query_payment_status(self, merchant_reference: str, tracking_id: str) -> Dict:
        """
        Query the status of a payment.
        
        Args:
            merchant_reference: Your transaction reference
            tracking_id: Pesapal tracking ID
            
        Returns:
            Dict with payment status information
        """
        logger.info(f"Querying payment status for {merchant_reference}")
        
        url = f"{self.base_url}/QueryPaymentStatus"
        
        params = {
            "pesapal_merchant_reference": merchant_reference,
            "pesapal_transaction_tracking_id": tracking_id
        }
        
        try:
            auth = OAuth1(
                self.consumer_key,
                self.consumer_secret,
                signature_method='HMAC-SHA1',
                signature_type='query'
            )
            
            response = requests.get(
                url,
                params=params,
                auth=auth,
                timeout=30
            )
            
            logger.debug(f"Status query response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                # Response format: pesapal_response_data=<reference>,<tracking_id>,<status>,<payment_method>,<amount>,<created_date>
                data = response.text.strip()
                
                if "pesapal_response_data=" in data:
                    parts = data.split("=")[1].split(",")
                    
                    if len(parts) >= 3:
                        status = parts[2].upper()
                        
                        return {
                            "success": True,
                            "reference": parts[0] if len(parts) > 0 else merchant_reference,
                            "tracking_id": parts[1] if len(parts) > 1 else tracking_id,
                            "status": status,
                            "payment_method": parts[3] if len(parts) > 3 else None,
                            "amount": parts[4] if len(parts) > 4 else None,
                            "paid": status in ["COMPLETED", "SUCCESS"]
                        }
                
                return {
                    "success": False,
                    "error": "Invalid response format from Pesapal"
                }
            else:
                logger.error(f"Status query failed: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Query failed: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Payment status query error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
