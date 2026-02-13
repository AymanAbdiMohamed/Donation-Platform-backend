"""
Mock M-Pesa callback simulator.

Simulates realistic M-Pesa STK Push flow with time delays.
"""
import time
import random
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def simulate_mpesa_callback(checkout_request_id, phone, amount, app):
    """
    Simulate M-Pesa callback after a short delay (5 seconds).
    
    Args:
        checkout_request_id: The checkout request ID
        phone: Customer phone number
        amount: Amount in KES
        app: Flask app instance (for context)
    """
    # Short delay for snappier demo
    delay = 5.0
    logger.info(f"⏱️ Mock M-Pesa: Waiting {delay:.1f}s before callback for {checkout_request_id}")
    
    time.sleep(delay)
    
    # Generate realistic receipt number
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    receipt_number = f"QGK{timestamp[:8]}{random.randint(1000, 9999)}"
    
    logger.info(f"✅ Mock M-Pesa: Simulating successful payment callback")
    
    # Simulate the callback payload that Safaricom would send
    callback_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": f"GR_{int(time.time())}_MOCK",
                "CheckoutRequestID": checkout_request_id,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": amount},
                        {"Name": "MpesaReceiptNumber", "Value": receipt_number},
                        {"Name": "TransactionDate", "Value": int(timestamp)},
                        {"Name": "PhoneNumber", "Value": int(phone)}
                    ]
                }
            }
        }
    }
    
    # Process the callback using the app context
    with app.app_context():
        from app.services.donation_service import DonationService
        
        try:
            # Use the official callback processor
            result = DonationService.process_stk_callback(callback_payload)
            if result.get("success"):
                logger.info(f"✅ Mock callback processed successfully for {checkout_request_id}")
            else:
                logger.error(f"❌ Mock callback processing failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Mock callback error: {e}")


def start_mock_callback(checkout_request_id, phone, amount, app):
    """
    Start the mock callback simulation in a background thread.
    
    Args:
        checkout_request_id: The checkout request ID
        phone: Customer phone number  
        amount: Amount in KES
        app: Flask app instance
    """
    thread = threading.Thread(
        target=simulate_mpesa_callback,
        args=(checkout_request_id, phone, amount, app),
        daemon=True
    )
    thread.start()
    logger.info(f"🚀 Mock callback thread started for {checkout_request_id}")
