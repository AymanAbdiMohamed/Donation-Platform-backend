"""
Public Routes.

Routes accessible without authentication.
"""
from flask import Blueprint, jsonify

from app.services import CharityService

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
