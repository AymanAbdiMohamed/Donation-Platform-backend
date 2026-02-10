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
from app.extensions import limiter

admin_bp = Blueprint("admin", __name__)


# ==================
# User Management
# ==================

@admin_bp.route("/users", methods=["GET"])
@role_required("admin")
def get_users():
    """
    Get all users on the platform (paginated).
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        role: Filter by role (optional)
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        
    Returns:
        200: Paginated list of users
    """
    role = request.args.get("role")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    
    query = User.query
    if role:
        query = query.filter_by(role=role)
    
    pagination = query.order_by(User.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        "users": [u.to_dict() for u in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
    }), 200


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@role_required("admin")
def get_user(user_id):
    """
    Get a specific user by ID.
    
    Args:
        user_id: User ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: User details
        404: User not found
    """
    user = UserService.get_user(user_id)
    
    if not user:
        return not_found("User not found")
    
    return jsonify({"user": user.to_dict()}), 200


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@role_required("admin")
@limiter.limit("30 per minute")
def deactivate_user(user_id):
    """
    Deactivate a user account.
    
    Args:
        user_id: User ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: User deactivated
        400: Cannot deactivate self or other admins
        404: User not found
    """
    from flask_jwt_extended import get_jwt_identity
    
    current_user_id = int(get_jwt_identity())
    
    # Prevent self-deactivation
    if user_id == current_user_id:
        return bad_request("Cannot deactivate your own account")
    
    user = UserService.get_user(user_id)
    
    if not user:
        return not_found("User not found")
    
    # Prevent deactivating other admins
    if user.role == "admin":
        return bad_request("Cannot deactivate admin accounts")
    
    user.is_active = False
    from app.extensions import db
    db.session.commit()
    
    return jsonify({
        "message": "User deactivated",
        "user": user.to_dict()
    }), 200


@admin_bp.route("/users/<int:user_id>/activate", methods=["POST"])
@role_required("admin")
@limiter.limit("30 per minute")
def activate_user(user_id):
    """
    Reactivate a deactivated user account.
    
    Args:
        user_id: User ID
        
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: User activated
        404: User not found
    """
    user = UserService.get_user(user_id)
    
    if not user:
        return not_found("User not found")
    
    user.is_active = True
    from app.extensions import db
    db.session.commit()
    
    return jsonify({
        "message": "User activated",
        "user": user.to_dict()
    }), 200


# ==================
# Application Management
# ==================

@admin_bp.route("/applications", methods=["GET"])
@role_required("admin")
def get_applications():
    """
    Get all charity applications (paginated).
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        status: Filter by status (pending, approved, rejected)
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        
    Returns:
        200: Paginated list of applications
    """
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    
    # Frontend sends ?status=pending but the model stores "submitted".
    # See CharityApplication.VALID_STATUSES for canonical values.
    if status == "pending":
        status = "submitted"
    
    query = CharityApplication.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(CharityApplication.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        "applications": [a.to_dict() for a in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
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
@limiter.limit("30 per minute")
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
@limiter.limit("30 per minute")
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
    Get all charities (including inactive, paginated).
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        active: Filter by active status (true/false)
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        
    Returns:
        200: Paginated list of charities
    """
    active = request.args.get("active")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    
    query = Charity.query
    if active is not None:
        is_active = active.lower() == "true"
        query = query.filter_by(is_active=is_active)
    
    pagination = query.order_by(Charity.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        "charities": [c.to_dict() for c in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
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
    pending_count = CharityApplication.query.filter_by(status="submitted").count()
    approved_count = CharityApplication.query.filter_by(status="approved").count()
    rejected_count = CharityApplication.query.filter_by(status="rejected").count()
    
    return jsonify({
        "total_users": total_users,
        "total_donors": total_donors,
        "total_charity_users": total_charity_users,
        "total_charities": total_charities,
        "total_donations": total_donations,
        "total_donations_kes": total_donations / 100,
        "donation_count": donation_count,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count
    }), 200
