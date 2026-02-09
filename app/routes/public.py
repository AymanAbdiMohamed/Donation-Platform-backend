"""
Public Routes.

Routes accessible without authentication.
"""
from flask import Blueprint, jsonify

from app.services import CharityService
from app.errors import not_found

public_bp = Blueprint("public", __name__)


@public_bp.route("/charities", methods=["GET"])
def get_charities():
    """
    Get list of all active charities (public access).
    
    Returns:
        200: List of active charities
    """
    charities = CharityService.get_active_charities()
    
    return jsonify({
        "charities": [c.to_dict() for c in charities]
    }), 200


@public_bp.route("/charities/<int:charity_id>", methods=["GET"])
def get_charity(charity_id):
    """
    Get a specific active charity by ID (public access).

    Args:
        charity_id: Charity ID

    Returns:
        200: Charity details with stats
        404: Charity not found
    """
    charity = CharityService.get_charity(charity_id)

    if not charity or not charity.is_active:
        return not_found("Charity not found")

    stats = CharityService.get_charity_stats(charity_id)

    return jsonify({
        "charity": charity.to_dict(),
        "stats": stats
    }), 200
