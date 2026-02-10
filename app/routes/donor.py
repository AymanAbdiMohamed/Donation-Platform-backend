"""
Donor Routes.

Routes for donor users to browse charities and make donations.
"""
import re

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth import role_required
from app.services import CharityService, DonationService, ReceiptService, PaymentService
from app.errors import bad_request, not_found
from app.extensions import limiter

donor_bp = Blueprint("donor", __name__)

# Simple regex for Kenyan phone numbers: 254XXXXXXXXX (12 digits)
_PHONE_RE = re.compile(r"^254\d{9}$")


def _normalise_phone(raw):
    """Normalise a phone number to 254XXXXXXXXX.  Returns None on failure."""
    raw = str(raw).strip().replace(" ", "").replace("-", "")
    if raw.startswith("+"):
        raw = raw[1:]
    if raw.startswith("0"):
        raw = "254" + raw[1:]
    if _PHONE_RE.match(raw):
        return raw
    return None


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


# ── M-Pesa donation endpoint (single source of truth) ──────────────────

@donor_bp.route("/donate/mpesa", methods=["POST"])
@role_required("donor")
@limiter.limit("10 per minute")
def donate_mpesa():
    """
    Initiate an M-Pesa STK Push donation.

    POST /donor/donate/mpesa
    Authorization: Bearer <JWT>

    Body:
        {
            "charity_id": 1,
            "amount": 500,
            "phone_number": "254712345678",
            "message": "optional",
            "is_anonymous": false
        }

    The backend:
      1. Validates input
      2. Creates a PENDING donation row in the DB
      3. Fires STK Push to the donor's phone
      4. Returns immediately — the donation is finalised asynchronously
         when Safaricom calls our callback endpoint.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return bad_request("Request body is required")

    charity_id = data.get("charity_id")
    amount = data.get("amount")
    phone_raw = data.get("phone_number")

    if not all([charity_id, amount, phone_raw]):
        return bad_request("charity_id, amount, and phone_number are required")

    # Validate amount
    try:
        amount_num = float(amount)
        if amount_num <= 0:
            return bad_request("Amount must be positive")
        if amount_num != int(amount_num):
            return bad_request("Amount must be a whole number (KES, no decimals)")
    except (ValueError, TypeError):
        return bad_request("Invalid amount")

    # Validate phone
    phone = _normalise_phone(phone_raw)
    if not phone:
        return bad_request(
            "Invalid phone number. Use format 254XXXXXXXXX or 07XXXXXXXX"
        )

    # Validate charity
    charity = CharityService.get_charity(charity_id)
    if not charity or not charity.is_active:
        return not_found("Charity not found or inactive")

    # Check M-Pesa is configured
    if not PaymentService.is_configured():
        return bad_request(
            "M-Pesa payments are not configured on this server. "
            "Please contact the administrator."
        )

    try:
        result = DonationService.initiate_mpesa_donation(
            donor_id=user_id,
            charity_id=charity_id,
            amount_kes=int(amount_num),
            phone_number=phone,
            is_anonymous=data.get("is_anonymous", False),
            message=data.get("message", "").strip() or None,
            account_reference=charity.name[:12] if charity.name else "SheNeeds",
        )

        return jsonify({
            "message": "STK Push sent. Please check your phone to complete payment.",
            "donation": result["donation"].to_dict(),
            "checkout_request_id": result["checkout_request_id"],
            "customer_message": result.get("customer_message", ""),
        }), 200

    except ValueError as e:
        return bad_request(str(e))


# ── Legacy simple donation (removed) ────────────────────────────────────
# POST /donor/donate was a test/dev-only simple donation endpoint
# (no M‑Pesa, amount in cents).  Removed to eliminate dead code.
# Use POST /donor/donate/mpesa  or POST /api/donations/mpesa instead.


@donor_bp.route("/donations", methods=["GET"])
@role_required("donor")
def get_donations():
    """Get donor's donation history (paginated)."""
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    from app.models import Donation
    pagination = Donation.query.filter_by(donor_id=user_id).order_by(
        Donation.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "donations": [d.to_dict() for d in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
    }), 200


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


# ── Donation status polling ─────────────────────────────────────────────

@donor_bp.route("/donations/<int:donation_id>/status", methods=["GET"])
@role_required("donor")
def get_donation_status(donation_id):
    """
    Poll the status of a donation.

    Used by the frontend after initiating an STK Push to check whether
    the payment has been completed.
    """
    user_id = int(get_jwt_identity())
    donation = DonationService.get_donation(donation_id)

    if not donation or donation.donor_id != user_id:
        return not_found("Donation not found")

    return jsonify({
        "id": donation.id,
        "status": donation.status,
        "mpesa_receipt_number": donation.mpesa_receipt_number,
        "amount_kes": donation.amount_kes,
        "charity_name": donation.charity.name if donation.charity else None,
    }), 200
