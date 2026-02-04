"""
Admin routes blueprint.

BE2 Day 1 - Route Review:
- All routes in this file should be admin-only
- Admin routes handle: user management, charity approval/rejection, platform oversight
- These routes require @role_required('admin') decorator for protection
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

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
    return jsonify({"message": "Admin access granted", "route": "get_all_users"}), 200


@admin_bp.route("/applications", methods=["GET"])
@jwt_required()
@role_required("admin")
def get_charity_applications():
    """
    Get all charity applications.
    Admin-only: Review pending charity applications.
    """
    return jsonify({"message": "Admin access granted", "route": "get_charity_applications"}), 200


@admin_bp.route("/applications/<int:app_id>/approve", methods=["POST"])
@jwt_required()
@role_required("admin")
def approve_application(app_id):
    """
    Approve a charity application.
    Admin-only: Approve pending charity applications.
    """
    return jsonify({"message": "Admin access granted", "route": "approve_application", "app_id": app_id}), 200


@admin_bp.route("/applications/<int:app_id>/reject", methods=["POST"])
@jwt_required()
@role_required("admin")
def reject_application(app_id):
    """
    Reject a charity application.
    Admin-only: Reject pending charity applications with reason.
    """
    return jsonify({"message": "Admin access granted", "route": "reject_application", "app_id": app_id}), 200
