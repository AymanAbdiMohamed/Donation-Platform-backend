"""
Payment Routes — M-Pesa Daraja callbacks.

These endpoints are called by Safaricom, not by our frontend.
No JWT auth — Safaricom does not send bearer tokens.
"""
import ipaddress
from functools import wraps
from flask import Blueprint, request, jsonify, current_app

from app.services import DonationService

payment_bp = Blueprint("payment", __name__)

# Safaricom IP ranges for M-Pesa callbacks (as of 2026)
# These should be periodically verified with Safaricom documentation
SAFARICOM_IP_RANGES = [
    # Production IP ranges
    "196.201.214.0/24",
    "196.201.215.0/24",
    "196.201.212.0/24",
    "196.201.213.0/24",
    # Additional Safaricom ranges
    "102.22.0.0/16",  # Safaricom cloud
]

# Parse CIDR networks once at module load
_ALLOWED_NETWORKS = [ipaddress.ip_network(cidr) for cidr in SAFARICOM_IP_RANGES]


def _get_client_ip():
    """
    Extract the client IP address, considering reverse proxies.
    
    On Render and other platforms, the real IP is in X-Forwarded-For.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        # First IP in the chain is the original client
        return forwarded.split(",")[0].strip()
    return request.remote_addr


def _is_safaricom_ip(ip_str):
    """
    Check if an IP address belongs to Safaricom's known ranges.
    
    In sandbox/development mode, we allow all IPs since testing
    may come from various sources.
    """
    # Skip validation in sandbox mode
    if current_app.config.get("MPESA_ENV") == "sandbox":
        return True
    
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in _ALLOWED_NETWORKS)
    except ValueError:
        current_app.logger.warning("Invalid IP address: %s", ip_str)
        return False


def verify_safaricom_callback(f):
    """
    Decorator to verify callback requests come from Safaricom IPs.
    
    In production, rejects requests from unknown IP addresses.
    In sandbox mode, allows all IPs for testing convenience.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = _get_client_ip()
        
        if not _is_safaricom_ip(client_ip):
            current_app.logger.warning(
                "M-Pesa callback from unauthorized IP: %s", client_ip
            )
            # Still return 200 to avoid retry storms, but log the attempt
            # In production, you might want to return 403 instead
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
        
        # Log the callback source
        current_app.logger.info("M-Pesa callback from IP: %s", client_ip)
        
        return f(*args, **kwargs)
    return decorated_function


@payment_bp.route("/callback", methods=["POST"])
@verify_safaricom_callback
def mpesa_callback():
    """
    M-Pesa STK Push callback.

    Called by Safaricom after the customer completes (or cancels) the payment
    on their phone.

    Expected body (from Safaricom docs):
        {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "...",
                    "CheckoutRequestID": "...",
                    "ResultCode": 0,
                    "ResultDesc": "...",
                    "CallbackMetadata": { "Item": [...] }
                }
            }
        }

    The donation row was already created (status=PENDING) by
    ``DonationService.initiate_mpesa_donation`` when the STK push was
    fired.  This callback simply transitions the donation to SUCCESS or
    FAILED.
    """
    try:
        callback_data = request.get_json(silent=True)
    except Exception:
        callback_data = None

    if not callback_data or not isinstance(callback_data, dict):
        current_app.logger.warning("M-Pesa callback received empty/invalid payload")
        # Safaricom expects 200 + ResultCode 0 to stop retries.
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

    current_app.logger.info("M-Pesa callback received: %s", callback_data)

    try:
        result = DonationService.process_stk_callback(callback_data)
    except Exception as exc:
        current_app.logger.exception("Unhandled error processing M-Pesa callback: %s", exc)
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

    if result.get("success"):
        current_app.logger.info(
            "Donation id=%s finalised as %s (receipt=%s)",
            result.get("donation_id"),
            result.get("donation_status"),
            result.get("mpesa_receipt_number", "N/A"),
        )
    elif result.get("already_processed"):
        current_app.logger.info(
            "Callback for already-processed donation id=%s (status=%s)",
            result.get("donation_id"),
            result.get("donation_status"),
        )
    else:
        current_app.logger.error(
            "M-Pesa callback processing failed: %s", result.get("error")
        )

    # Safaricom expects 200 + ResultCode 0 to stop retries.
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


@payment_bp.route("/timeout", methods=["POST"])
@verify_safaricom_callback
def mpesa_timeout():
    """
    M-Pesa timeout notification.

    Safaricom hits this when they could not reach our callback URL within
    their internal timeout window.  We just log and acknowledge.
    """
    try:
        payload = request.get_json(silent=True)
    except Exception:
        payload = None
    current_app.logger.warning("M-Pesa timeout notification: %s", payload)
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
