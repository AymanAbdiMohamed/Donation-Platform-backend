"""
Pesapal payment routes.

Handles payment callbacks and status queries.
"""
from flask import Blueprint, request, jsonify, redirect, current_app
from app.services import DonationService
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
            
            # Find donation by reference
            donation = DonationService.get_donation_by_checkout_id(merchant_ref)
            
            if donation:
                if donation.status != "PAID":
                    # Update to PAID
                    DonationService.update_donation_status(
                        donation_id=donation.id,
                        status="PAID",
                        mpesa_receipt=tracking_id
                    )
                    logger.info(f"Donation {donation.id} marked as PAID")
                else:
                    logger.info(f"Donation {donation.id} already marked as PAID")
            else:
                logger.warning(f"No donation found for reference {merchant_ref}")
        else:
            logger.info(f"Payment not completed for {merchant_ref}: status={status_result.get('status')}")
        
        # Pesapal expects "pesapal_notification_type=CHANGE" response
        return f"pesapal_notification_type={notification_type}", 200
        
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
