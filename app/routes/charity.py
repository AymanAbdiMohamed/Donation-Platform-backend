"""
Charity Routes.

Routes for charity users to manage their profile, applications, and view donations.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth import role_required
from app.extensions import db
from app.services import CharityService, DonationService
from app.utils.file_upload import (
    save_uploaded_file,
    generate_storage_path
)
from app.errors import bad_request, not_found, conflict

charity_bp = Blueprint("charity", __name__)


# ==================
# Application Routes
# ==================

@charity_bp.route("/apply", methods=["POST"])
@role_required("charity")
def apply():
    """
    Create or update a charity application draft (Step 1).

    Request Body:
        name: Charity name (required)
        description: Charity description (optional)
        step: Current step (optional)
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return bad_request("Request body is required")

    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    step = data.get("step", 1)

    if not name:
        return bad_request("Charity name is required")

    try:
        application = CharityService.get_latest_application(user_id)

        if application and application.status == "draft":
            application = CharityService.save_application_step(
                user_id=user_id,
                step_data={
                    "name": name,
                    "description": description
                }
            )
            if 1 <= step <= application.TOTAL_STEPS:
                application.step = step
                db.session.commit()

            return jsonify({
                "message": "Application draft updated successfully",
                "application": application.to_dict()
            }), 200

        application = CharityService.create_application(
            user_id=user_id,
            name=name,
            description=description
        )

        return jsonify({
            "message": "Application draft created successfully",
            "application": application.to_dict()
        }), 201

    except ValueError as e:
        return conflict(str(e))


@charity_bp.route("/apply/step/<int:step>", methods=["PUT"])
@role_required("charity")
def save_application_step(step):
    """
    Save data for a specific application step.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return bad_request("Request body is required")

    if step < 1 or step > 4:
        return bad_request("Step must be between 1 and 4")

    step_fields = {
        1: ["name", "description", "category"],
        2: ["mission", "goals"],
        3: [
            "registration_number", "country",
            "location", "address",
            "contact_email", "contact_phone", "website"
        ],
        4: []  # documents only
    }

    allowed_fields = step_fields[step]
    step_data = {k: v for k, v in data.items() if k in allowed_fields}

    if allowed_fields and not step_data:
        return bad_request(f"No valid fields provided for step {step}")

    application = CharityService.get_latest_application(user_id)
    if not application:
        return not_found("No application found")

    application = CharityService.save_application_step(user_id, step_data)
    application.step = step
    db.session.commit()

    return jsonify({
        "message": f"Step {step} saved successfully",
        "application": application.to_dict()
    }), 200


@charity_bp.route("/apply/submit", methods=["POST"])
@role_required("charity")
def submit_application():
    """Submit application for review."""
    user_id = int(get_jwt_identity())

    try:
        application = CharityService.submit_application(user_id)
        return jsonify({
            "message": "Application submitted successfully",
            "application": application.to_dict()
        }), 200
    except ValueError as e:
        return conflict(str(e))


@charity_bp.route("/application", methods=["GET"])
@role_required("charity")
def get_application():
    """Get current charity application."""
    user_id = int(get_jwt_identity())
    application = CharityService.get_latest_application(user_id)

    return jsonify({
        "application": application.to_dict() if application else None
    }), 200


@charity_bp.route("/application/documents", methods=["POST"])
@role_required("charity")
def upload_document():
    """Upload application documents."""
    user_id = int(get_jwt_identity())

    document_type = request.form.get("document_type")
    if not document_type:
        return bad_request("Document type is required")

    if "file" not in request.files:
        return bad_request("File is required")

    file = request.files["file"]
    application = CharityService.get_latest_application(user_id)

    if not application:
        return not_found("No application found")

    storage_path = generate_storage_path(
        file_type="documents",
        user_id=user_id,
        filename=file.filename
    )

    success, result = save_uploaded_file(file, storage_path)
    if not success:
        return bad_request(result)

    from app.models import CharityDocument

    document = CharityDocument(
        application_id=application.id,
        document_type=document_type,
        file_path=result["path"],
        original_filename=file.filename,
        file_size=result.get("size"),
        mime_type=file.content_type
    )

    db.session.add(document)
    db.session.commit()

    return jsonify({
        "message": "Document uploaded successfully",
        "document": document.to_dict()
    }), 201


@charity_bp.route("/application/documents", methods=["GET"])
@role_required("charity")
def get_documents():
    """Get application documents."""
    user_id = int(get_jwt_identity())
    application = CharityService.get_latest_application(user_id)

    if not application:
        return not_found("No application found")

    documents = CharityService.get_application_documents(application.id)

    return jsonify({
        "documents": [d.to_dict() for d in documents]
    }), 200


# ==================
# Profile Routes
# ==================

@charity_bp.route("/profile", methods=["GET"])
@role_required("charity")
def get_profile():
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)

    if not charity:
        return not_found("Charity not found or pending approval")

    return jsonify({"charity": charity.to_dict()}), 200


@charity_bp.route("/profile", methods=["PUT"])
@role_required("charity")
def update_profile():
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)

    if not charity:
        return not_found("Charity not found")

    if request.content_type and "multipart/form-data" in request.content_type:
        data = request.form
        files = request.files
    else:
        data = request.get_json()
        files = None

    if not data:
        return bad_request("Request body is required")

    updates = {}
    fields = [
        "name", "description", "category", "location",
        "contact_email", "contact_phone", "website",
        "address", "mission", "goals"
    ]

    for field in fields:
        if field in data and data[field] is not None:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            if field in ("name", "description") and not value:
                continue
            updates[field] = value

    if files and "logo" in files:
        logo = files["logo"]
        if logo.filename:
            path = generate_storage_path("logos", user_id, logo.filename)
            success, result = save_uploaded_file(logo, path)
            if not success:
                return bad_request(result)
            updates["logo_path"] = result["path"]

    if not updates:
        return bad_request("No valid fields to update")

    charity = CharityService.update_charity(charity.id, **updates)

    return jsonify({
        "message": "Profile updated successfully",
        "charity": charity.to_dict()
    }), 200


# ==================
# Donation Routes
# ==================

@charity_bp.route("/donations", methods=["GET"])
@role_required("charity")
def get_donations():
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)

    if not charity:
        return not_found("Charity not found")

    limit = request.args.get("limit", type=int)
    donations = DonationService.get_donations_by_charity(charity.id, limit)

    return jsonify({
        "donations": [d.to_dict(include_donor=True) for d in donations]
    }), 200


# ==================
# Dashboard Route
# ==================

@charity_bp.route("/dashboard", methods=["GET"])
@role_required("charity")
def dashboard():
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)

    if not charity:
        return not_found("Charity not found")

    stats = CharityService.get_charity_stats(charity.id)
    recent = DonationService.get_donations_by_charity(charity.id, limit=5)

    return jsonify({
        "charity": charity.to_dict(),
        "stats": stats,
        "recent_donations": [d.to_dict(include_donor=True) for d in recent]
    }), 200
