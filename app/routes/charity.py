"""
Charity Routes.

Routes for charity users to manage their profile and view donations.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.auth import role_required
from app.services import CharityService, DonationService
from app.errors import bad_request, not_found, conflict

charity_bp = Blueprint("charity", __name__)


# ==================
# Application Routes
# ==================

@charity_bp.route("/apply", methods=["POST"])
@role_required("charity")
def apply():
    """
    Submit a charity application.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Request Body:
        name: Charity name (required)
        description: Charity description (optional)
        contact_email: Contact email (optional)
        contact_phone: Contact phone (optional)
        registration_number: Registration number (optional)
        country: Country of operation (optional)
        
    Returns:
        201: Application submitted successfully
        400: Invalid request data
        409: Application already exists or charity already approved
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data:
        return bad_request("Request body is required")
    
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    contact_email = data.get("contact_email", "").strip() or None
    contact_phone = data.get("contact_phone", "").strip() or None
    registration_number = data.get("registration_number", "").strip() or None
    country = data.get("country", "").strip() or None
    
    if not name:
        return bad_request("Charity name is required")
    
    try:
        application = CharityService.create_application(
            user_id=user_id,
            name=name,
            description=description,
            contact_email=contact_email,
            contact_phone=contact_phone,
            registration_number=registration_number,
            country=country
        )
        
        return jsonify({
            "message": "Application submitted successfully",
            "application": application.to_dict()
        }), 201
        
    except ValueError as e:
        return conflict(str(e))


@charity_bp.route("/application", methods=["GET"])
@role_required("charity")
def get_application():
    """
    Get current user's charity application status.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Application details or null if no application
    """
    user_id = int(get_jwt_identity())
    application = CharityService.get_latest_application(user_id)
    
    return jsonify({
        "application": application.to_dict() if application else None
    }), 200


# ==================
# Profile Routes
# ==================

@charity_bp.route("/profile", methods=["GET"])
@role_required("charity")
def get_profile():
    """
    Get charity profile.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Charity profile
        404: Charity not found (application may be pending)
    """
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    
    if not charity:
        return not_found("Charity not found. Your application may still be pending.")
    
    return jsonify({"charity": charity.to_dict()}), 200


@charity_bp.route("/profile", methods=["PUT"])
@role_required("charity")
def update_profile():
    """
    Update charity profile.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Request Body:
        name: New charity name (optional)
        description: New description (optional)
        
    Returns:
        200: Profile updated successfully
        400: Invalid request data
        404: Charity not found
    """
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    
    if not charity:
        return not_found("Charity not found")
    
    data = request.get_json()
    if not data:
        return bad_request("Request body is required")
    
    # Build update kwargs
    updates = {}
    if "name" in data and data["name"].strip():
        updates["name"] = data["name"].strip()
    if "description" in data:
        updates["description"] = data["description"].strip()
    
    if not updates:
        return bad_request("No valid fields to update")
    
    updated_charity = CharityService.update_charity(charity.id, **updates)
    
    return jsonify({
        "message": "Profile updated successfully",
        "charity": updated_charity.to_dict()
    }), 200


# ==================
# Donation Routes
# ==================

@charity_bp.route("/donations", methods=["GET"])
@role_required("charity")
def get_donations():
    """
    Get donations received by the charity.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        limit: Optional limit on number of results
        
    Returns:
        200: List of received donations
        404: Charity not found
    """
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    
    if not charity:
        return not_found("Charity not found")
    
    limit = request.args.get("limit", type=int)
    donations = DonationService.get_donations_by_charity(charity.id, limit=limit)
    
    return jsonify({
        "donations": [d.to_dict(include_donor=True) for d in donations]
    }), 200


# ==================
# Dashboard Routes
# ==================

@charity_bp.route("/dashboard", methods=["GET"])
@role_required("charity")
def dashboard():
    """
    Get charity dashboard with stats and recent donations.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Dashboard data including stats and recent donations
        404: Charity not found
    """
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    
    if not charity:
        return not_found("Charity not found")
    
    # Get statistics
    stats = CharityService.get_charity_stats(charity.id)
    
    # Get recent donations
    recent_donations = DonationService.get_donations_by_charity(charity.id, limit=5)
    
    return jsonify({
        "charity": charity.to_dict(),
        "stats": stats,
        "recent_donations": [d.to_dict(include_donor=True) for d in recent_donations]
    }), 200
