"""
Admin routes blueprint.
All routes are admin-only.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime
from db import SessionLocal
from models import CharityApplication, Charity
from auth import role_required

admin_bp = Blueprint("admin", __name__)

# =========================
# Admin-only routes
# =========================

@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@role_required("admin")
def get_all_users():
    """
    Get all users.
    Admin-only: View all registered users on the platform.
    """
    session = SessionLocal()
    try:
        # Placeholder: Fetch all users (replace with actual User model)
        users = []  # Replace with: session.query(User).all()
        return jsonify({"users": [user.to_dict() for user in users]}), 200
    finally:
        session.close()


@admin_bp.route("/applications", methods=["GET"])
@jwt_required()
@role_required("admin")
def get_charity_applications():
    """
    Get all charity applications.
    Admin-only: Review pending charity applications.
    """
    status = request.args.get("status")
    session = SessionLocal()
    try:
        query = session.query(CharityApplication)
        if status:
            query = query.filter_by(status=status)
        applications = query.order_by(CharityApplication.created_at.desc()).all()
        return jsonify({
            "applications": [app.to_dict() for app in applications]
        }), 200
    finally:
        session.close()


@admin_bp.route("/applications/<int:app_id>/approve", methods=["POST"])
@jwt_required()
@role_required("admin")
def approve_application(app_id):
    """
    Approve a charity application.
    Admin-only: Approve pending charity applications.
    """
    session = SessionLocal()
    try:
        application = session.query(CharityApplication).get(app_id)
        if not application:
            return jsonify({
                "error": "Application not found",
                "message": f"No application found with ID {app_id}"
            }), 404

        if application.status != "pending":
            return jsonify({
                "error": "Invalid status",
                "message": f"Application is already {application.status}"
            }), 400

        # Update application
        application.status = "approved"
        application.reviewed_at = datetime.utcnow()

        # Create charity
        charity = Charity(
            name=application.name,
            description=application.description,
            user_id=application.user_id
        )

        session.add(charity)
        session.commit()
        session.refresh(charity)

        return jsonify({
            "message": "Application approved successfully",
            "application": application.to_dict(),
            "charity": charity.to_dict()
        }), 200

    except Exception:
        session.rollback()
        return jsonify({
            "error": "Approval failed",
            "message": "Unable to approve application"
        }), 500
    finally:
        session.close()


@admin_bp.route("/applications/<int:app_id>/reject", methods=["POST"])
@jwt_required()
@role_required("admin")
def reject_application(app_id):
    """
    Reject a charity application.
    Admin-only: Reject pending charity applications with reason.
    """
    data = request.get_json() or {}
    reason = data.get("reason", "").strip()

    session = SessionLocal()
    try:
        application = session.query(CharityApplication).get(app_id)
        if not application:
            return jsonify({
                "error": "Application not found",
                "message": f"No application found with ID {app_id}"
            }), 404

        if application.status != "pending":
            return jsonify({
                "error": "Invalid status",
                "message": f"Application is already {application.status}"
            }), 400

        application.status = "rejected"
        application.rejection_reason = reason
        application.reviewed_at = datetime.utcnow()

        session.commit()

        return jsonify({
            "message": "Application rejected successfully",
            "application": application.to_dict()
        }), 200

    except Exception:
        session.rollback()
        return jsonify({
            "error": "Rejection failed",
            "message": "Unable to reject application"
        }), 500
    finally:
        session.close()
