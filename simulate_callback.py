import sys
import requests
import json
import time

def simulate_callback(phone_number="254712345678", amount=100, checkout_request_id=None):
    """Simulate a successful M-Pesa callback."""
    
    if not checkout_request_id:
        print("Error: checkout_request_id required")
        return

    url = "http://localhost:5000/api/mpesa/callback"
    
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": f"GR_{int(time.time())}",
                "CheckoutRequestID": checkout_request_id,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": amount},
                        {"Name": "MpesaReceiptNumber", "Value": f"MCK{int(time.time())}"},
                        {"Name": "TransactionDate", "Value": str(int(time.time()))},
                        {"Name": "PhoneNumber", "Value": int(phone_number)}
                    ]
                }
            }
        }
    }
    
    try:
        print(f"Sending mock callback to {url}...")
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to send callback: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simulate_callback.py <CheckoutRequestID> [Amount] [Phone]")
        sys.exit(1)
        
    checkout_id = sys.argv[1]
    amt = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    phone = sys.argv[3] if len(sys.argv) > 3 else "254712345678"
    
    simulate_callback(phone_number=phone, amount=amt, checkout_request_id=checkout_id)
