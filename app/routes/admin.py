"""
Admin Routes.

Routes for admin users to manage the platform.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.auth import role_required
from app.services import UserService, CharityService, DonationService
from app.models import User, Charity, CharityApplication
from app.errors import bad_request, not_found

admin_bp = Blueprint("admin", __name__)


# ==================
# User Management
# ==================

@admin_bp.route("/users", methods=["GET"])
@role_required("admin")
def get_users():
    """
    Get all users on the platform.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        role: Filter by role (optional)
        
    Returns:
        200: List of users
    """
    role = request.args.get("role")
    
    if role:
        users = User.query.filter_by(role=role).all()
    else:
        users = UserService.get_all_users()
    
    return jsonify({
        "users": [u.to_dict() for u in users]
    }), 200


# ==================
# Application Management
# ==================

@admin_bp.route("/applications", methods=["GET"])
@role_required("admin")
def get_applications():
    """
    Get all charity applications.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        status: Filter by status (pending, approved, rejected)
        
    Returns:
        200: List of applications
    """
    status = request.args.get("status")
    applications = CharityService.get_applications_by_status(status)
    
    return jsonify({
        "applications": [a.to_dict() for a in applications]
    }), 200


@admin_bp.route("/applications/<int:app_id>", methods=["GET"])
@role_required("admin")
def get_application(app_id):
    """
    Get a specific application.
    
    Args:
        app_id: Application ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Application details
        404: Application not found
    """
    application = CharityService.get_application(app_id)
    
    if not application:
        return not_found("Application not found")
    
    return jsonify({"application": application.to_dict()}), 200


@admin_bp.route("/applications/<int:app_id>/approve", methods=["POST"])
@role_required("admin")
def approve_application(app_id):
    """
    Approve a charity application.
    
    Args:
        app_id: Application ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Application approved, charity created
        400: Application already processed
        404: Application not found
    """
    try:
        application, charity = CharityService.approve_application(app_id)
        
        return jsonify({
            "message": "Application approved successfully",
            "application": application.to_dict(),
            "charity": charity.to_dict()
        }), 200
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            return not_found(error_msg)
        return bad_request(error_msg)


@admin_bp.route("/applications/<int:app_id>/reject", methods=["POST"])
@role_required("admin")
def reject_application(app_id):
    """
    Reject a charity application.
    
    Args:
        app_id: Application ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Request Body:
        reason: Rejection reason (optional)
        
    Returns:
        200: Application rejected
        400: Application already processed
        404: Application not found
    """
    data = request.get_json() or {}
    reason = data.get("reason", "").strip()
    
    try:
        application = CharityService.reject_application(app_id, reason)
        
        return jsonify({
            "message": "Application rejected",
            "application": application.to_dict()
        }), 200
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            return not_found(error_msg)
        return bad_request(error_msg)


# ==================
# Charity Management
# ==================

@admin_bp.route("/charities", methods=["GET"])
@role_required("admin")
def get_charities():
    """
    Get all charities (including inactive).
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        active: Filter by active status (true/false)
        
    Returns:
        200: List of charities
    """
    active = request.args.get("active")
    
    if active is not None:
        is_active = active.lower() == "true"
        charities = Charity.query.filter_by(is_active=is_active).all()
    else:
        charities = CharityService.get_all_charities()
    
    return jsonify({
        "charities": [c.to_dict() for c in charities]
    }), 200


@admin_bp.route("/charities/<int:charity_id>", methods=["GET"])
@role_required("admin")
def get_charity(charity_id):
    """
    Get details of a specific charity.
    
    Args:
        charity_id: Charity ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Charity details with stats
        404: Charity not found
    """
    charity = CharityService.get_charity(charity_id)
    
    if not charity:
        return not_found("Charity not found")
    
    stats = CharityService.get_charity_stats(charity_id)
    
    return jsonify({
        "charity": charity.to_dict(),
        "stats": stats
    }), 200


@admin_bp.route("/charities/<int:charity_id>", methods=["DELETE"])
@role_required("admin")
def deactivate_charity(charity_id):
    """
    Deactivate a charity.
    
    Args:
        charity_id: Charity ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Charity deactivated
        404: Charity not found
    """
    charity = CharityService.deactivate_charity(charity_id)
    
    if not charity:
        return not_found("Charity not found")
    
    return jsonify({
        "message": "Charity deactivated",
        "charity": charity.to_dict()
    }), 200


@admin_bp.route("/charities/<int:charity_id>/activate", methods=["POST"])
@role_required("admin")
def activate_charity(charity_id):
    """
    Reactivate a deactivated charity.
    
    Args:
        charity_id: Charity ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Charity activated
        404: Charity not found
    """
    charity = CharityService.activate_charity(charity_id)
    
    if not charity:
        return not_found("Charity not found")
    
    return jsonify({
        "message": "Charity activated",
        "charity": charity.to_dict()
    }), 200


# ==================
# Platform Statistics
# ==================

@admin_bp.route("/stats", methods=["GET"])
@role_required("admin")
def get_stats():
    """
    Get platform-wide statistics.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Platform statistics
    """
    total_users = User.query.count()
    total_donors = User.query.filter_by(role="donor").count()
    total_charity_users = User.query.filter_by(role="charity").count()
    total_charities = Charity.query.filter_by(is_active=True).count()
    total_donations = DonationService.get_total_donations_amount()
    donation_count = DonationService.get_total_donation_count()
    pending_count = CharityApplication.query.filter_by(status="pending").count()
    approved_count = CharityApplication.query.filter_by(status="approved").count()
    rejected_count = CharityApplication.query.filter_by(status="rejected").count()
    
    return jsonify({
        "total_users": total_users,
        "total_donors": total_donors,
        "total_charity_users": total_charity_users,
        "total_charities": total_charities,
        "total_donations": total_donations,
        "total_donations_dollars": total_donations / 100,
        "donation_count": donation_count,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count
    }), 200
