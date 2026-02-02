"""
ALL routes in ONE file.
Sections: Auth, Donor, Charity, Admin
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from datetime import datetime
from db import db
from models import User, Charity, CharityApplication, Donation
from auth import role_required

api = Blueprint("api", __name__)


# =============================================================================
# AUTH ROUTES
# =============================================================================

@api.route("/auth/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "donor")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    if role not in ["donor", "charity"]:
        return jsonify({"error": "Role must be 'donor' or 'charity'"}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409
    
    user = User(email=email, role=role)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    access_token = create_access_token(
        identity=user.id,
        additional_claims={"role": user.role}
    )
    
    return jsonify({
        "message": "Registration successful",
        "access_token": access_token,
        "user": user.to_dict()
    }), 201


@api.route("/auth/login", methods=["POST"])
def login():
    """Authenticate user and return JWT."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401
    
    access_token = create_access_token(
        identity=user.id,
        additional_claims={"role": user.role}
    )
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": user.to_dict()
    }), 200


@api.route("/auth/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current authenticated user."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({"user": user.to_dict()}), 200


# =============================================================================
# DONOR ROUTES
# =============================================================================

@api.route("/donor/charities", methods=["GET"])
@jwt_required()
@role_required("donor")
def get_charities():
    """Get list of all active charities."""
    charities = Charity.query.filter_by(is_active=True).all()
    return jsonify({
        "charities": [c.to_dict() for c in charities]
    }), 200


@api.route("/donor/donate", methods=["POST"])
@jwt_required()
@role_required("donor")
def donate():
    """Make a donation to a charity."""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    charity_id = data.get("charity_id")
    amount = data.get("amount")  # in cents
    is_anonymous = data.get("is_anonymous", False)
    is_recurring = data.get("is_recurring", False)
    message = data.get("message", "")
    
    if not charity_id or not amount:
        return jsonify({"error": "charity_id and amount are required"}), 400
    
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400
    
    charity = Charity.query.filter_by(id=charity_id, is_active=True).first()
    if not charity:
        return jsonify({"error": "Charity not found or inactive"}), 404
    
    donation = Donation(
        amount=amount,
        donor_id=user_id,
        charity_id=charity_id,
        is_anonymous=is_anonymous,
        is_recurring=is_recurring,
        message=message
    )
    
    db.session.add(donation)
    db.session.commit()
    
    return jsonify({
        "message": "Donation successful",
        "donation": donation.to_dict(include_donor=True)
    }), 201


@api.route("/donor/donations", methods=["GET"])
@jwt_required()
@role_required("donor")
def get_donor_donations():
    """Get donor's donation history."""
    user_id = get_jwt_identity()
    donations = Donation.query.filter_by(donor_id=user_id).order_by(Donation.created_at.desc()).all()
    
    return jsonify({
        "donations": [d.to_dict(include_donor=True) for d in donations]
    }), 200


# =============================================================================
# CHARITY ROUTES
# =============================================================================

@api.route("/charity/apply", methods=["POST"])
@jwt_required()
@role_required("charity")
def apply_charity():
    """Submit a charity application."""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    name = data.get("name")
    description = data.get("description", "")
    
    if not name:
        return jsonify({"error": "Charity name is required"}), 400
    
    # Check for existing pending application
    existing = CharityApplication.query.filter_by(user_id=user_id, status="pending").first()
    if existing:
        return jsonify({"error": "You already have a pending application"}), 409
    
    # Check if already approved charity
    existing_charity = Charity.query.filter_by(user_id=user_id).first()
    if existing_charity:
        return jsonify({"error": "You already have an approved charity"}), 409
    
    application = CharityApplication(
        user_id=user_id,
        name=name,
        description=description
    )
    
    db.session.add(application)
    db.session.commit()
    
    return jsonify({
        "message": "Application submitted",
        "application": application.to_dict()
    }), 201


@api.route("/charity/application", methods=["GET"])
@jwt_required()
@role_required("charity")
def get_my_application():
    """Get current user's charity application status."""
    user_id = get_jwt_identity()
    application = CharityApplication.query.filter_by(user_id=user_id).order_by(CharityApplication.created_at.desc()).first()
    
    if not application:
        return jsonify({"application": None}), 200
    
    return jsonify({"application": application.to_dict()}), 200


@api.route("/charity/profile", methods=["GET"])
@jwt_required()
@role_required("charity")
def get_charity_profile():
    """Get charity profile."""
    user_id = get_jwt_identity()
    charity = Charity.query.filter_by(user_id=user_id).first()
    
    if not charity:
        return jsonify({"error": "Charity not found. Application may be pending."}), 404
    
    return jsonify({"charity": charity.to_dict()}), 200


@api.route("/charity/profile", methods=["PUT"])
@jwt_required()
@role_required("charity")
def update_charity_profile():
    """Update charity profile."""
    user_id = get_jwt_identity()
    charity = Charity.query.filter_by(user_id=user_id).first()
    
    if not charity:
        return jsonify({"error": "Charity not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if "name" in data:
        charity.name = data["name"]
    if "description" in data:
        charity.description = data["description"]
    
    db.session.commit()
    
    return jsonify({
        "message": "Profile updated",
        "charity": charity.to_dict()
    }), 200


@api.route("/charity/donations", methods=["GET"])
@jwt_required()
@role_required("charity")
def get_charity_donations():
    """Get donations received by charity."""
    user_id = get_jwt_identity()
    charity = Charity.query.filter_by(user_id=user_id).first()
    
    if not charity:
        return jsonify({"error": "Charity not found"}), 404
    
    donations = Donation.query.filter_by(charity_id=charity.id).order_by(Donation.created_at.desc()).all()
    
    return jsonify({
        "donations": [d.to_dict(include_donor=True) for d in donations]
    }), 200


@api.route("/charity/dashboard", methods=["GET"])
@jwt_required()
@role_required("charity")
def charity_dashboard():
    """Get charity dashboard stats."""
    user_id = get_jwt_identity()
    charity = Charity.query.filter_by(user_id=user_id).first()
    
    if not charity:
        return jsonify({"error": "Charity not found"}), 404
    
    total_donations = db.session.query(db.func.sum(Donation.amount)).filter_by(charity_id=charity.id).scalar() or 0
    donation_count = Donation.query.filter_by(charity_id=charity.id).count()
    recent = Donation.query.filter_by(charity_id=charity.id).order_by(Donation.created_at.desc()).limit(5).all()
    
    return jsonify({
        "charity": charity.to_dict(),
        "stats": {
            "total_donations": total_donations,
            "donation_count": donation_count
        },
        "recent_donations": [d.to_dict(include_donor=True) for d in recent]
    }), 200


# =============================================================================
# ADMIN ROUTES
# =============================================================================

@api.route("/admin/applications", methods=["GET"])
@jwt_required()
@role_required("admin")
def get_applications():
    """Get all charity applications."""
    status = request.args.get("status")  # optional filter
    
    query = CharityApplication.query
    if status:
        query = query.filter_by(status=status)
    
    applications = query.order_by(CharityApplication.created_at.desc()).all()
    
    return jsonify({
        "applications": [a.to_dict() for a in applications]
    }), 200


@api.route("/admin/applications/<int:id>/approve", methods=["POST"])
@jwt_required()
@role_required("admin")
def approve_application(id):
    """Approve a charity application."""
    application = CharityApplication.query.get(id)
    
    if not application:
        return jsonify({"error": "Application not found"}), 404
    
    if application.status != "pending":
        return jsonify({"error": "Application already processed"}), 400
    
    # Update application
    application.status = "approved"
    application.reviewed_at = datetime.utcnow()
    
    # Create charity
    charity = Charity(
        name=application.name,
        description=application.description,
        user_id=application.user_id
    )
    
    db.session.add(charity)
    db.session.commit()
    
    return jsonify({
        "message": "Application approved",
        "application": application.to_dict(),
        "charity": charity.to_dict()
    }), 200


@api.route("/admin/applications/<int:id>/reject", methods=["POST"])
@jwt_required()
@role_required("admin")
def reject_application(id):
    """Reject a charity application."""
    application = CharityApplication.query.get(id)
    
    if not application:
        return jsonify({"error": "Application not found"}), 404
    
    if application.status != "pending":
        return jsonify({"error": "Application already processed"}), 400
    
    data = request.get_json() or {}
    reason = data.get("reason", "")
    
    application.status = "rejected"
    application.rejection_reason = reason
    application.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        "message": "Application rejected",
        "application": application.to_dict()
    }), 200


@api.route("/admin/charities", methods=["GET"])
@jwt_required()
@role_required("admin")
def admin_get_charities():
    """Get all charities (admin)."""
    charities = Charity.query.all()
    return jsonify({
        "charities": [c.to_dict() for c in charities]
    }), 200


@api.route("/admin/charities/<int:id>", methods=["DELETE"])
@jwt_required()
@role_required("admin")
def delete_charity(id):
    """Deactivate a charity."""
    charity = Charity.query.get(id)
    
    if not charity:
        return jsonify({"error": "Charity not found"}), 404
    
    charity.is_active = False
    db.session.commit()
    
    return jsonify({
        "message": "Charity deactivated",
        "charity": charity.to_dict()
    }), 200


@api.route("/admin/stats", methods=["GET"])
@jwt_required()
@role_required("admin")
def admin_stats():
    """Get platform statistics."""
    total_users = User.query.count()
    total_charities = Charity.query.filter_by(is_active=True).count()
    total_donations = db.session.query(db.func.sum(Donation.amount)).scalar() or 0
    pending_applications = CharityApplication.query.filter_by(status="pending").count()
    
    return jsonify({
        "stats": {
            "total_users": total_users,
            "total_charities": total_charities,
            "total_donations": total_donations,
            "pending_applications": pending_applications
        }
    }), 200
