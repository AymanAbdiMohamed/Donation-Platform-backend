"""
Pesapal payment routes.

Handles payment callbacks and status queries.
"""
from flask import Blueprint, request, jsonify, redirect, current_app
from app.services import DonationService
from app.models.donation import DonationStatus
from app.extensions import db
from app.utils.pesapal import PesapalClient
import logging

logger = logging.getLogger(__name__)

pesapal_bp = Blueprint("pesapal", __name__, url_prefix="/api/pesapal")


@pesapal_bp.route("/callback", methods=["GET"])
def pesapal_callback():
    """
    Handle Pesapal IPN callback.

    Pesapal sends: ?pesapal_merchant_reference=XXX&pesapal_transaction_tracking_id=YYY&pesapal_notification_type=CHANGE
    """
    merchant_ref = request.args.get("pesapal_merchant_reference")
    tracking_id = request.args.get("pesapal_transaction_tracking_id")
    notification_type = request.args.get("pesapal_notification_type")

    logger.info(f"Pesapal callback received: ref={merchant_ref}, tracking={tracking_id}, type={notification_type}")

    if not merchant_ref or not tracking_id:
        logger.error("Missing required parameters in Pesapal callback")
        return "Invalid callback", 400

    try:
        # Query payment status
        client = PesapalClient()
        status_result = client.query_payment_status(merchant_ref, tracking_id)

        if not status_result.get("success"):
            logger.error(f"Failed to query payment status: {status_result.get('error')}")
            return "Error querying status", 500

        # Update donation based on status
        if status_result.get("paid"):
            logger.info(f"Payment confirmed for {merchant_ref}")

            # Find donation by reference (correct method name)
            donation = DonationService.get_donation_by_checkout(merchant_ref)

            if donation:
                if donation.status != DonationStatus.SUCCESS:
                    # Update to SUCCESS using direct ORM update
                    donation.status = DonationStatus.SUCCESS
                    donation.mpesa_receipt_number = tracking_id
                    db.session.commit()
                    logger.info(f"Donation {donation.id} marked as SUCCESS")
                else:
                    logger.info(f"Donation {donation.id} already marked as SUCCESS")
            else:
                logger.warning(f"No donation found for reference {merchant_ref}")
        else:
            logger.info(f"Payment not completed for {merchant_ref}: status={status_result.get('status')}")

        # Pesapal expects a plain-text acknowledgement; use a fixed string, not
        # the raw query-param value, to avoid reflecting untrusted input.
        return "pesapal_notification_type=CHANGE", 200

    except Exception as e:
        logger.error(f"Error processing Pesapal callback: {e}")
        return "Internal error", 500


@pesapal_bp.route("/status/<reference>", methods=["GET"])
def check_payment_status(reference):
    """
    Check payment status for a given reference.

    Used by frontend to poll payment status.
    """
    tracking_id = request.args.get("tracking_id")

    if not tracking_id:
        return jsonify({"error": "tracking_id required"}), 400

    try:
        client = PesapalClient()
        result = client.query_payment_status(reference, tracking_id)

        if result.get("success"):
            return jsonify({
                "status": result.get("status"),
                "paid": result.get("paid", False),
                "payment_method": result.get("payment_method"),
                "amount": result.get("amount")
            })
        else:
            return jsonify({"error": result.get("error")}), 500

    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return jsonify({"error": str(e)}), 500
