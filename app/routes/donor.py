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


# ── Charity browsing ────────────────────────────────────────────────

@donor_bp.route("/charities", methods=["GET"])
@role_required("donor")
def get_charities():
    """Get list of active charities."""
    charities = CharityService.get_active_charities()
    # Standardized response format (matches public /charities endpoint)
    return jsonify({
        "charities": [c.to_dict() for c in charities],
        "pagination": {
            "page": 1,
            "per_page": len(charities),
            "total": len(charities),
            "pages": 1,
        }
    }), 200


@donor_bp.route("/charities/<int:charity_id>", methods=["GET"])
@role_required("donor")
def get_charity(charity_id):
    """Get charity details."""
    charity = CharityService.get_charity(charity_id)
    if not charity or not charity.is_active:
        return not_found("Charity not found")
    stats = CharityService.get_charity_stats(charity_id)
    return jsonify({"charity": charity.to_dict(), "stats": stats}), 200


# ── Legacy/simple donation (no payment gateway) ────────────────────

@donor_bp.route("/donate", methods=["POST"])
@role_required("donor")
def make_donation():
    """Simple donation (amount in cents, no payment gateway)."""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return bad_request("Request body is required")

    charity_id = data.get("charity_id")
    amount = data.get("amount")  # cents
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
        message=message,
    )
    return jsonify({
        "message": "Donation created successfully",
        "donation": donation.to_dict(),
    }), 201


# ── Donor donations and dashboard ────────────────────────────────

@donor_bp.route("/donations", methods=["GET"])
@role_required("donor")
def get_donations():
    """Get donor's donation history (paginated)."""
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    result = DonationService.get_donations_by_donor(
        donor_id=user_id,
        page=page,
        per_page=per_page,
    )
    return jsonify({
        "donations": [d.to_dict() for d in result["donations"]],
        "total": result["total"],
        "page": result["page"],
        "per_page": result["per_page"],
        "pages": result["pages"],
    })


@donor_bp.route("/donations", methods=["POST"])
@role_required("donor")
def create_donation_direct():
    """Create donation record directly (e.g., after external payment)."""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return bad_request("Request body is required")

    charity_id = data.get("charity_id")
    amount = data.get("amount")  # dollars from frontend
    if not all([charity_id, amount]):
        return bad_request("charity_id and amount are required")

    try:
        amount_cents = int(float(amount) * 100)
        donation = DonationService.create_donation_after_payment(
            checkout_request_id=f"DIRECT-{user_id}",
            donor_id=user_id,
            charity_id=charity_id,
            amount_cents=amount_cents,
            transaction_id=f"TXN-{user_id}",
            is_anonymous=data.get("is_anonymous", False),
            is_recurring=data.get("is_recurring", False),
            message=data.get("message", "").strip()
        )
        return jsonify({
            "message": "Donation recorded successfully",
            "donation": donation.to_dict()
        }), 201
    except ValueError as e:
        return bad_request(str(e))


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


# ── Donation receipt endpoints ──────────────────────────────────

@donor_bp.route("/donations/<int:donation_id>/receipt", methods=["GET"])
@role_required("donor")
def get_donation_receipt(donation_id):
    """Get receipt for a specific donation (must belong to donor)."""
    user_id = int(get_jwt_identity())
    donation = DonationService.get_donation(donation_id)
    if not donation or donation.donor_id != user_id:
        return not_found("Donation not found")

    try:
        receipt = ReceiptService.generate_receipt(donation_id)
        return jsonify({"receipt": receipt}), 200
    except ValueError as e:
        return not_found(str(e))


@donor_bp.route("/donations/<int:donation_id>/receipt/email", methods=["POST"])
@role_required("donor")
def email_donation_receipt(donation_id):
    """Email receipt for a donation to the donor."""
    user_id = int(get_jwt_identity())
    donation = DonationService.get_donation(donation_id)
    if not donation or donation.donor_id != user_id:
        return not_found("Donation not found")

    try:
        ReceiptService.send_receipt_email(donation_id)
        return jsonify({"message": "Receipt sent to your email"}), 200
    except ValueError as e:
        return not_found(str(e))


# ── Donation status polling ────────────────────────────────────

@donor_bp.route("/donations/<int:donation_id>/status", methods=["GET"])
@role_required("donor")
def get_donation_status(donation_id):
    """Poll the status of a donation (for STK Push)."""
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


# ── Additional donor info ─────────────────────────────────────

@donor_bp.route("/stats", methods=["GET"])
@role_required("donor")
def get_stats():
    """Get donor statistics."""
    user_id = int(get_jwt_identity())
    stats = DonationService.get_donor_stats(user_id)
    return jsonify(stats), 200


@donor_bp.route("/favorites", methods=["GET"])
@role_required("donor")
def get_favorites():
    """Get donor's favorite charities (Placeholder)."""
    return jsonify({"favorites": []}), 200


@donor_bp.route("/recurring", methods=["GET"])
@role_required("donor")
def get_recurring():
    """Get donor's recurring donations."""
    user_id = int(get_jwt_identity())
    recurring = DonationService.get_recurring_donations(user_id)
    return jsonify({"recurring": [d.to_dict() for d in recurring]}), 200
