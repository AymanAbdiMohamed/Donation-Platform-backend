"""
Donor Routes.

Routes for donor users to browse charities and make donations.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth import role_required
from app.services import CharityService, DonationService, ReceiptService, PaymentService
from app.errors import bad_request, not_found

donor_bp = Blueprint("donor", __name__)


@donor_bp.route("/charities", methods=["GET"])
@role_required("donor")
def get_charities():
    """Get list of active charities."""
    charities = CharityService.get_active_charities()
    return jsonify({"charities": [c.to_dict() for c in charities]}), 200


@donor_bp.route("/charities/<int:charity_id>", methods=["GET"])
@role_required("donor")
def get_charity(charity_id):
    """Get charity details."""
    charity = CharityService.get_charity(charity_id)
    if not charity or not charity.is_active:
        return not_found("Charity not found")
    
    stats = CharityService.get_charity_stats(charity_id)
    return jsonify({"charity": charity.to_dict(), "stats": stats}), 200


@donor_bp.route("/donate", methods=["POST"])
@role_required("donor")
def make_donation():
    """Initiate donation with M-Pesa payment."""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data:
        return bad_request("Request body is required")
    
    charity_id = data.get("charity_id")
    amount = data.get("amount")
    phone_number = data.get("phone_number")
    
    if not all([charity_id, amount, phone_number]):
        return bad_request("charity_id, amount, and phone_number are required")
    
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            return bad_request("Amount must be positive")
    except (ValueError, TypeError):
        return bad_request("Invalid amount")
    
    charity = CharityService.get_charity(charity_id)
    if not charity or not charity.is_active:
        return not_found("Charity not found or inactive")
    
    if not PaymentService.is_configured():
        return bad_request(
            "M-Pesa payments are not configured. "
            "Set MPESA_* environment variables or use POST /donor/donations for the simple flow."
        )

    try:
        result = DonationService.initiate_donation(
            donor_id=user_id,
            charity_id=charity_id,
            amount=amount_float,
            phone_number=phone_number,
            is_anonymous=data.get("is_anonymous", False),
            is_recurring=data.get("is_recurring", False),
            message=data.get("message", "").strip()
        )

        # Store pending donation data so the callback route can create the record
        from app.routes.payment import store_pending_donation
        store_pending_donation(
            result["checkout_request_id"],
            result["pending_donation"]
        )
        
        return jsonify({
            "message": "Payment initiated. Please complete on your phone.",
            "checkout_request_id": result["checkout_request_id"],
            "customer_message": result.get("customer_message")
        }), 200
        
    except ValueError as e:
        return bad_request(str(e))


@donor_bp.route("/donations", methods=["GET"])
@role_required("donor")
def get_donations():
    """Get donor's donation history."""
    user_id = int(get_jwt_identity())
    limit = request.args.get("limit", type=int)
    donations = DonationService.get_donations_by_donor(user_id, limit=limit)
    return jsonify({"donations": [d.to_dict() for d in donations]}), 200


@donor_bp.route("/dashboard", methods=["GET"])
@role_required("donor")
def dashboard():
    """Get donor dashboard stats."""
    user_id = int(get_jwt_identity())
    stats = DonationService.get_donor_stats(user_id)
    recent_donations = DonationService.get_donations_by_donor(user_id, limit=5)
    
    return jsonify({
        "stats": stats,
        "recent_donations": [d.to_dict() for d in recent_donations]
    }), 200


@donor_bp.route("/donations", methods=["POST"])
@role_required("donor")
def create_donation():
    """Create a donation (simple flow without payment gateway)."""
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return bad_request("Request body is required")

    charity_id = data.get("charity_id")
    amount = data.get("amount")  # Amount in cents

    if not charity_id or amount is None:
        return bad_request("charity_id and amount are required")

    try:
        amount_cents = int(amount)
        if amount_cents <= 0:
            return bad_request("Amount must be positive")
    except (ValueError, TypeError):
        return bad_request("Invalid amount")

    charity = CharityService.get_charity(charity_id)
    if not charity or not charity.is_active:
        return not_found("Charity not found or inactive")

    message = data.get("message")
    if message and len(message) > 500:
        return bad_request("Message must be 500 characters or fewer")
    
    donation = DonationService.create_donation(
        donor_id=user_id,
        charity_id=charity_id,
        amount_cents=amount_cents,
        is_anonymous=data.get("is_anonymous", False),
        is_recurring=data.get("is_recurring", False),
        message=message
    )

    return jsonify({
        "message": "Donation created successfully",
        "donation": donation.to_dict()
    }), 201


@donor_bp.route("/donations/<int:donation_id>/receipt", methods=["GET"])
@role_required("donor")
def get_donation_receipt(donation_id):
    """Get receipt for a specific donation (must belong to the requesting donor)."""
    user_id = int(get_jwt_identity())

    donation = DonationService.get_donation(donation_id)
    if not donation:
        return not_found("Donation not found")

    if donation.donor_id != user_id:
        return not_found("Donation not found")

    try:
        receipt = ReceiptService.generate_receipt(donation_id)
        return jsonify({"receipt": receipt}), 200
    except ValueError as e:
        return not_found(str(e))


@donor_bp.route("/donations/<int:donation_id>/receipt/email", methods=["POST"])
@role_required("donor")
def email_donation_receipt(donation_id):
    """Email receipt for a specific donation to the donor."""
    user_id = int(get_jwt_identity())

    donation = DonationService.get_donation(donation_id)
    if not donation:
        return not_found("Donation not found")

    if donation.donor_id != user_id:
        return not_found("Donation not found")

    try:
        ReceiptService.send_receipt_email(donation_id)
        return jsonify({"message": "Receipt sent to your email"}), 200
    except ValueError as e:
        return not_found(str(e))
