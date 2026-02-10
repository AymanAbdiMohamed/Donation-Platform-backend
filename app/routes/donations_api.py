"""
Donations API Routes.

Single source of truth for donation endpoints consumed by the frontend.
All routes require JWT authentication.

Prefix: /api/donations  (registered in app factory)
"""
import re

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth import role_required
from app.services import CharityService, DonationService, PaymentService
from app.errors import bad_request, not_found
from app.extensions import limiter

donations_api_bp = Blueprint("donations_api", __name__)

# Simple regex for Kenyan phone numbers: 254XXXXXXXXX (12 digits)
_PHONE_RE = re.compile(r"^254\d{9}$")


def _normalise_phone(raw):
    """Normalise a phone number to 254XXXXXXXXX. Returns None on failure."""
    raw = str(raw).strip().replace(" ", "").replace("-", "")
    if raw.startswith("+"):
        raw = raw[1:]
    if raw.startswith("0"):
        raw = "254" + raw[1:]
    if _PHONE_RE.match(raw):
        return raw
    return None


@donations_api_bp.route("/mpesa", methods=["POST"])
@role_required("donor")
@limiter.limit("10 per minute")
def initiate_mpesa_donation():
    """
    Initiate an M-Pesa STK Push donation.

    POST /api/donations/mpesa
    Authorization: Bearer <JWT>

    Request body:
        {
            "charity_id": 1,
            "amount": 500,
            "phone_number": "254712345678",
            "message": "optional",
            "is_anonymous": false
        }

    The backend:
      1. Validates JWT + input
      2. Creates a PENDING donation row
      3. Fires STK Push to the donor's phone
      4. Returns immediately — donation finalised asynchronously via callback

    Response 200:
        {
            "message": "STK Push sent. Check your phone to complete payment.",
            "donation": { ... },
            "checkout_request_id": "...",
            "customer_message": "..."
        }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return bad_request("Request body is required")

    charity_id = data.get("charity_id")
    amount = data.get("amount")
    phone_raw = data.get("phone_number")

    # ── Validate required fields ────────────────────────────────────────
    if not all([charity_id, amount, phone_raw]):
        return bad_request("charity_id, amount, and phone_number are required")

    # ── Validate amount ─────────────────────────────────────────────────
    try:
        amount_num = float(amount)
        if amount_num <= 0:
            return bad_request("Amount must be positive")
        if amount_num != int(amount_num):
            return bad_request("Amount must be a whole number (KES, no decimals)")
    except (ValueError, TypeError):
        return bad_request("Invalid amount")

    # ── Validate phone ──────────────────────────────────────────────────
    phone = _normalise_phone(phone_raw)
    if not phone:
        return bad_request(
            "Invalid phone number. Use format 254XXXXXXXXX or 07XXXXXXXX"
        )

    # ── Validate charity ────────────────────────────────────────────────
    charity = CharityService.get_charity(charity_id)
    if not charity or not charity.is_active:
        return not_found("Charity not found or inactive")

    # ── Check M-Pesa is configured ─────────────────────────────────────
    if not PaymentService.is_configured():
        return jsonify({
            "error": "Service unavailable",
            "message": (
                "M-Pesa payments are not configured on this server. "
                "Please contact the administrator."
            ),
        }), 503

    # ── Initiate donation + STK Push ────────────────────────────────────
    try:
        result = DonationService.initiate_mpesa_donation(
            donor_id=user_id,
            charity_id=charity_id,
            amount_kes=int(amount_num),
            phone_number=phone,
            is_anonymous=data.get("is_anonymous", False),
            message=data.get("message", "").strip() or None,
            account_reference=charity.name[:12] if charity.name else "Donation",
        )

        return jsonify({
            "message": "STK Push sent. Check your phone to complete payment.",
            "donation": result["donation"].to_dict(),
            "checkout_request_id": result["checkout_request_id"],
            "customer_message": result.get("customer_message", ""),
        }), 200

    except ValueError as exc:
        return bad_request(str(exc))


@donations_api_bp.route("/<int:donation_id>/status", methods=["GET"])
@role_required("donor")
def get_donation_status(donation_id):
    """
    Poll the status of a donation.

    GET /api/donations/<id>/status
    Authorization: Bearer <JWT>

    Used by the frontend after initiating an STK Push to check whether
    the payment has been completed.

    Response 200:
        {
            "id": 1,
            "status": "PENDING" | "SUCCESS" | "FAILED",
            "mpesa_receipt_number": "...",
            "amount": 50000,
            "charity_name": "..."
        }
    """
    user_id = int(get_jwt_identity())
    donation = DonationService.get_donation(donation_id)

    if not donation or donation.donor_id != user_id:
        return not_found("Donation not found")

    return jsonify({
        "id": donation.id,
        "status": donation.status,
        "mpesa_receipt_number": donation.mpesa_receipt_number,
        "amount": donation.amount,
        "amount_kes": donation.amount_kes,
        "charity_name": donation.charity.name if donation.charity else None,
    }), 200


@donations_api_bp.route("/status/<checkout_id>", methods=["GET"])
@role_required("donor")
def get_donation_status_by_checkout(checkout_id):
    """
    Poll the status of a donation by checkout request ID.

    GET /api/donations/status/<checkout_id>
    Authorization: Bearer <JWT>

    This is the preferred endpoint for polling after STK Push initiation,
    since the frontend receives the checkout_request_id immediately.

    Response 200:
        {
            "id": 1,
            "status": "PENDING" | "SUCCESS" | "FAILED",
            "mpesa_receipt_number": "...",
            "amount_kes": 500,
            "charity_name": "...",
            "created_at": "2026-02-10T12:00:00Z",
            "failure_reason": null
        }
    """
    user_id = int(get_jwt_identity())
    donation = DonationService.get_donation_by_checkout(checkout_id)

    if not donation:
        return not_found("Donation not found")

    # Verify ownership
    if donation.donor_id != user_id:
        return not_found("Donation not found")

    return jsonify({
        "id": donation.id,
        "status": donation.status,
        "mpesa_receipt_number": donation.mpesa_receipt_number,
        "amount": donation.amount,
        "amount_kes": donation.amount_kes,
        "charity_name": donation.charity.name if donation.charity else None,
        "created_at": donation.created_at.isoformat() if donation.created_at else None,
        "failure_reason": donation.failure_reason,
    }), 200
