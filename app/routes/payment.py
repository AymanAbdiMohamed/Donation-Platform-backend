"""
Payment Routes.

Handles payment gateway callbacks (M-Pesa Daraja).
These routes are called by external payment providers — no JWT auth required.
"""
import os
from flask import Blueprint, request, jsonify, current_app

from app.services import DonationService

payment_bp = Blueprint("payment", __name__)

# In-memory store for pending donations keyed by checkout_request_id.
# In production this should be replaced with Redis or a DB table.
_pending_donations = {}


def store_pending_donation(checkout_request_id, donation_data):
    """Store pending donation data after STK push initiation."""
    _pending_donations[checkout_request_id] = donation_data


def get_pending_donation(checkout_request_id):
    """Retrieve and remove pending donation data."""
    return _pending_donations.pop(checkout_request_id, None)


@payment_bp.route("/callback", methods=["POST"])
def mpesa_callback():
    """
    M-Pesa STK Push callback.

    Called by Safaricom after the customer completes (or cancels) the payment
    on their phone.  No authentication — M-Pesa does not send a JWT.

    Expected body shape (from Safaricom docs):
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
    """
    callback_data = request.get_json(silent=True)

    if not callback_data:
        return jsonify({"ResultCode": 1, "ResultDesc": "Invalid payload"}), 400

    # Extract the checkout_request_id to look up pending donation
    try:
        checkout_request_id = (
            callback_data.get("Body", {})
            .get("stkCallback", {})
            .get("CheckoutRequestID")
        )
    except (AttributeError, TypeError):
        checkout_request_id = None

    if not checkout_request_id:
        current_app.logger.warning("M-Pesa callback missing CheckoutRequestID")
        return jsonify({"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}), 400

    pending = get_pending_donation(checkout_request_id)

    if not pending:
        current_app.logger.warning(
            "No pending donation for CheckoutRequestID=%s", checkout_request_id
        )
        # Still acknowledge so M-Pesa doesn't keep retrying
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted (no pending donation)"}), 200

    result = DonationService.process_payment_callback(callback_data, pending)

    if result["success"]:
        current_app.logger.info(
            "Donation %s created via M-Pesa callback (txn=%s)",
            result["donation"].id,
            result.get("transaction_id"),
        )
    else:
        current_app.logger.error(
            "M-Pesa callback processing failed: %s", result.get("error")
        )

    # M-Pesa expects a 200 with ResultCode 0 to stop retries
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
