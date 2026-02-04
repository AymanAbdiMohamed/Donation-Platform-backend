"""
Donor Routes.

Routes for donor users to browse charities and make donations.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.auth import role_required
from app.services import CharityService, DonationService
from app.errors import bad_request, not_found

donor_bp = Blueprint("donor", __name__)


@donor_bp.route("/charities", methods=["GET"])
@role_required("donor")
def get_charities():
    """
    Get list of all active charities.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: List of active charities
    """
    charities = CharityService.get_active_charities()
    
    return jsonify({
        "charities": [c.to_dict() for c in charities]
    }), 200


@donor_bp.route("/charities/<int:charity_id>", methods=["GET"])
@role_required("donor")
def get_charity(charity_id):
    """
    Get details of a specific charity.
    
    Args:
        charity_id: Charity's ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Charity details
        404: Charity not found
    """
    charity = CharityService.get_charity(charity_id)
    
    if not charity or not charity.is_active:
        return not_found("Charity not found")
    
    return jsonify({"charity": charity.to_dict()}), 200


@donor_bp.route("/donate", methods=["POST"])
@role_required("donor")
def donate():
    """
    Make a donation to a charity.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Request Body:
        charity_id: ID of charity to donate to (required)
        amount: Donation amount in cents (required, must be positive)
        is_anonymous: Whether to hide donor info (default: false)
        is_recurring: Whether donation is recurring (default: false)
        message: Optional message to charity
        
    Returns:
        201: Donation created successfully
        400: Invalid request data
        404: Charity not found
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data:
        return bad_request("Request body is required")
    
    charity_id = data.get("charity_id")
    amount = data.get("amount")
    is_anonymous = data.get("is_anonymous", False)
    is_recurring = data.get("is_recurring", False)
    message = data.get("message", "")
    
    # Validation
    if not charity_id:
        return bad_request("charity_id is required")
    
    if not amount:
        return bad_request("amount is required")
    
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return bad_request("amount must be a number")
    
    if amount <= 0:
        return bad_request("amount must be positive")
    
    try:
        donation = DonationService.create_donation(
            donor_id=user_id,
            charity_id=charity_id,
            amount=amount,
            is_anonymous=is_anonymous,
            is_recurring=is_recurring,
            message=message
        )
        
        return jsonify({
            "message": "Donation successful",
            "donation": donation.to_dict(include_donor=True)
        }), 201
        
    except ValueError as e:
        error_msg = str(e)
        if "Charity not found" in error_msg:
            return not_found(error_msg)
        return bad_request(error_msg)


@donor_bp.route("/donations", methods=["GET"])
@role_required("donor")
def get_donations():
    """
    Get donor's donation history.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        limit: Optional limit on number of results
        
    Returns:
        200: List of donations made by the donor
    """
    user_id = int(get_jwt_identity())
    limit = request.args.get("limit", type=int)
    
    donations = DonationService.get_donations_by_donor(user_id, limit=limit)
    
    return jsonify({
        "donations": [d.to_dict(include_donor=True) for d in donations],
        "total_donated": DonationService.get_donor_total(user_id)
    }), 200
