"""
Beneficiary Routes.

Charity users can manage their beneficiary list and track inventory
(items distributed to each beneficiary).
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth import role_required
from app.extensions import db, limiter
from app.services import CharityService
from app.models import Beneficiary, InventoryItem
from app.errors import bad_request, not_found

beneficiaries_bp = Blueprint("beneficiaries", __name__)


# ── Beneficiary CRUD ──────────────────────────────────────────────

@beneficiaries_bp.route("/charity/beneficiaries", methods=["GET"])
@role_required("charity")
def get_beneficiaries():
    """Get all beneficiaries for the authenticated charity."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    include_inventory = request.args.get("include_inventory", "false").lower() == "true"
    beneficiaries = Beneficiary.query.filter_by(charity_id=charity.id).order_by(
        Beneficiary.created_at.desc()
    ).all()

    return jsonify({
        "beneficiaries": [b.to_dict(include_inventory=include_inventory) for b in beneficiaries]
    }), 200


@beneficiaries_bp.route("/charity/beneficiaries", methods=["POST"])
@role_required("charity")
@limiter.limit("20 per minute")
def create_beneficiary():
    """Add a new beneficiary."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    data = request.get_json()
    if not data:
        return bad_request("Request body is required")

    name = (data.get("name") or "").strip()
    if not name:
        return bad_request("Beneficiary name is required")
    if len(name) > 200:
        return bad_request("Name must be 200 characters or fewer")

    beneficiary = Beneficiary(
        charity_id=charity.id,
        name=name,
        age=data.get("age"),
        location=data.get("location"),
        school=data.get("school"),
        notes=data.get("notes"),
    )
    db.session.add(beneficiary)
    db.session.commit()

    return jsonify({
        "message": "Beneficiary added successfully",
        "beneficiary": beneficiary.to_dict()
    }), 201


@beneficiaries_bp.route("/charity/beneficiaries/<int:beneficiary_id>", methods=["PUT"])
@role_required("charity")
def update_beneficiary(beneficiary_id):
    """Update a beneficiary."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    beneficiary = Beneficiary.query.get(beneficiary_id)
    if not beneficiary or beneficiary.charity_id != charity.id:
        return not_found("Beneficiary not found")

    data = request.get_json()
    if not data:
        return bad_request("Request body is required")

    for field in ("name", "location", "school", "notes"):
        if field in data:
            value = data[field]
            if field == "name" and not (value or "").strip():
                return bad_request("Name cannot be empty")
            setattr(beneficiary, field, value)
    if "age" in data:
        beneficiary.age = data["age"]

    db.session.commit()

    return jsonify({
        "message": "Beneficiary updated",
        "beneficiary": beneficiary.to_dict()
    }), 200


@beneficiaries_bp.route("/charity/beneficiaries/<int:beneficiary_id>", methods=["DELETE"])
@role_required("charity")
def delete_beneficiary(beneficiary_id):
    """Delete a beneficiary and their inventory records."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    beneficiary = Beneficiary.query.get(beneficiary_id)
    if not beneficiary or beneficiary.charity_id != charity.id:
        return not_found("Beneficiary not found")

    db.session.delete(beneficiary)
    db.session.commit()

    return jsonify({"message": "Beneficiary removed"}), 200


# ── Inventory tracking ────────────────────────────────────────────

@beneficiaries_bp.route("/charity/beneficiaries/<int:beneficiary_id>/inventory", methods=["GET"])
@role_required("charity")
def get_inventory(beneficiary_id):
    """Get inventory items for a beneficiary."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    beneficiary = Beneficiary.query.get(beneficiary_id)
    if not beneficiary or beneficiary.charity_id != charity.id:
        return not_found("Beneficiary not found")

    items = InventoryItem.query.filter_by(beneficiary_id=beneficiary_id).order_by(
        InventoryItem.date_distributed.desc()
    ).all()

    return jsonify({
        "beneficiary": beneficiary.to_dict(),
        "inventory": [item.to_dict() for item in items]
    }), 200


@beneficiaries_bp.route("/charity/beneficiaries/<int:beneficiary_id>/inventory", methods=["POST"])
@role_required("charity")
@limiter.limit("30 per minute")
def add_inventory_item(beneficiary_id):
    """Add an inventory item distributed to a beneficiary."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    beneficiary = Beneficiary.query.get(beneficiary_id)
    if not beneficiary or beneficiary.charity_id != charity.id:
        return not_found("Beneficiary not found")

    data = request.get_json()
    if not data:
        return bad_request("Request body is required")

    item_name = (data.get("item_name") or "").strip()
    if not item_name:
        return bad_request("Item name is required")

    quantity = data.get("quantity", 1)
    try:
        quantity = int(quantity)
        if quantity < 1:
            return bad_request("Quantity must be at least 1")
    except (ValueError, TypeError):
        return bad_request("Invalid quantity")

    item = InventoryItem(
        beneficiary_id=beneficiary_id,
        item_name=item_name,
        quantity=quantity,
        notes=data.get("notes"),
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({
        "message": "Inventory item recorded",
        "item": item.to_dict()
    }), 201


@beneficiaries_bp.route("/charity/inventory/<int:item_id>", methods=["DELETE"])
@role_required("charity")
def delete_inventory_item(item_id):
    """Delete an inventory item."""
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    if not charity:
        return not_found("Charity not found")

    item = InventoryItem.query.get(item_id)
    if not item:
        return not_found("Item not found")

    beneficiary = Beneficiary.query.get(item.beneficiary_id)
    if not beneficiary or beneficiary.charity_id != charity.id:
        return not_found("Item not found")

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Item removed"}), 200
