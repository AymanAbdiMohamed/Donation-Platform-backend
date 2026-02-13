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
    Simulate M-Pesa callback after a realistic delay (30-40 seconds).
    
    This runs in a background thread to simulate the time it takes for:
    1. STK Push to reach the phone (5-10s)
    2. User to enter PIN and confirm (20-30s)
    3. M-Pesa to process and send callback (5s)
    
    Args:
        checkout_request_id: The checkout request ID
        phone: Customer phone number
        amount: Amount in KES
        app: Flask app instance (for context)
    """
    # Random delay between 30-40 seconds
    delay = random.uniform(30, 40)
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
        from app.services import DonationService
        
        try:
            # Extract callback data
            stk_callback = callback_payload["Body"]["stkCallback"]
            result_code = stk_callback.get("ResultCode")
            checkout_id = stk_callback.get("CheckoutRequestID")
            
            if result_code == 0:
                # Extract metadata
                metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
                receipt = next(
                    (item["Value"] for item in metadata if item["Name"] == "MpesaReceiptNumber"),
                    None
                )
                
                # Update donation to PAID
                donation = DonationService.get_donation_by_checkout_id(checkout_id)
                if donation:
                    DonationService.update_donation_status(
                        donation_id=donation.id,
                        status="PAID",
                        mpesa_receipt=receipt
                    )
                    logger.info(f"✅ Mock callback processed: Donation {donation.id} marked as PAID with receipt {receipt}")
                else:
                    logger.warning(f"⚠️ Mock callback: No donation found for {checkout_id}")
            else:
                logger.info(f"❌ Mock callback: Payment failed with code {result_code}")
                
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
