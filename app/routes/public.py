"""
Public Routes.

Routes accessible without authentication.
"""
from flask import Blueprint, jsonify, request

from app.services import CharityService
from app.models import Charity
from app.errors import not_found

public_bp = Blueprint("public", __name__)


@public_bp.route("/charities", methods=["GET"])
def get_charities():
    """
    Get list of all active charities (public access, paginated).
    
    Query Parameters:
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)

    Returns:
        200: Paginated list of active charities
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    pagination = Charity.query.filter_by(is_active=True).order_by(
        Charity.name
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "charities": [c.to_dict() for c in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
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
