"""
Charity routes blueprint.

BE2 Day 1 - Route Review:
- All routes in this file should be charity-only
- Charity routes handle: charity profile management, viewing received donations
- These routes require @role_required('charity') decorator for protection
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from auth import role_required

charity_bp = Blueprint("charity", __name__)


# =========================
# Charity-only routes
# =========================

@charity_bp.route("/profile", methods=["GET"])
@jwt_required()
@role_required("charity")
def get_charity_profile():
    """
    Get charity profile.
    Charity-only: View own charity profile details.
    """
    return jsonify({"message": "Charity access granted", "route": "get_charity_profile"}), 200


@charity_bp.route("/profile", methods=["PUT"])
@jwt_required()
@role_required("charity")
def update_charity_profile():
    """
    Update charity profile.
    Charity-only: Update own charity profile details.
    """
    return jsonify({"message": "Charity access granted", "route": "update_charity_profile"}), 200


@charity_bp.route("/donations", methods=["GET"])
@jwt_required()
@role_required("charity")
def get_charity_donations():
    """
    Get donations received by charity.
    Charity-only: View all donations made to this charity.
    """
    return jsonify({"message": "Charity access granted", "route": "get_charity_donations"}), 200


@charity_bp.route("/stats", methods=["GET"])
@jwt_required()
@role_required("charity")
def get_charity_stats():
    """
    Get charity statistics.
    Charity-only: View donation statistics and analytics.
    """
    return jsonify({"message": "Charity access granted", "route": "get_charity_stats"}), 200
