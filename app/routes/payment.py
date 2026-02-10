"""
Payment Routes — M-Pesa Daraja callbacks.

These endpoints are called by Safaricom, not by our frontend.
No JWT auth — Safaricom does not send bearer tokens.
"""
from flask import Blueprint, request, jsonify, current_app

from app.services import DonationService

payment_bp = Blueprint("payment", __name__)


@payment_bp.route("/callback", methods=["POST"])
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
