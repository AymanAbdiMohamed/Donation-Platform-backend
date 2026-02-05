"""
Charity Routes.

Routes for charity users to manage their profile, applications, and view donations.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.auth import role_required
from app.extensions import db
from app.services import CharityService, DonationService
from app.utils.file_upload import (
    save_uploaded_file, 
    ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
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
    Submit a charity application (Step 1: Create or update draft).
    
    Headers:
        Authorization: Bearer <access_token>
        
    Request Body:
        name: Charity name (required)
        description: Charity description (optional)
        step: Current step number (optional, default: 1)
        
    Returns:
        201: Application created/updated successfully
        400: Invalid request data
        409: Application already exists
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
        # Check if there's an existing draft
        existing = CharityService.get_latest_application(user_id)
        
        if existing and existing.status == "draft":
            # Update existing draft
            application = CharityService.save_application_step(
                user_id=user_id,
                step_data={"name": name, "description": description}
            )
            # Update step if provided
            if step and 1 <= step <= existing.TOTAL_STEPS:
                existing.step = step
                db.session.commit()
            
            return jsonify({
                "message": "Application draft updated successfully",
                "application": application.to_dict()
            }), 200
        else:
            # Create new application
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
    
    Headers:
        Authorization: Bearer <access_token>
        
    URL Parameters:
        step: Step number (1-4)
        
    Request Body:
        step_data: Dictionary of fields for this step
        
    Returns:
        200: Step saved successfully
        400: Invalid step number or data
        404: No application found
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data:
        return bad_request("Request body is required")
    
    if step < 1 or step > 4:
        return bad_request(f"Invalid step number: {step}. Must be between 1 and 4.")
    
    # Define fields per step
    step_fields = {
        1: ['name', 'description'],
        2: ['mission', 'goals'],
        3: ['category', 'location', 'contact_email', 'contact_phone', 'website', 'address'],
        4: []  # Step 4 is for documents only
    }
    
    allowed_fields = step_fields.get(step, [])
    
    # Filter data to only allowed fields
    step_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not step_data and allowed_fields:
        return bad_request(f"No valid fields provided for step {step}")
    
    try:
        # Get existing application
        application = CharityService.get_latest_application(user_id)
        
        if not application:
            return not_found("No application found. Please start a new application.")
        
        # Save step data
        application = CharityService.save_application_step(user_id, step_data)
        
        # Update step number
        application.step = step
        db.session.commit()
        
        return jsonify({
            "message": f"Step {step} saved successfully",
            "application": application.to_dict()
        }), 200
        
    except ValueError as e:
        return conflict(str(e))


@charity_bp.route("/apply/submit", methods=["POST"])
@role_required("charity")
def submit_application():
    """
    Submit a draft application for review.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Application submitted successfully
        400: Cannot submit (no application or already submitted)
        409: Conflict
    """
    user_id = int(get_jwt_identity())
    
    try:
        application = CharityService.submit_application(user_id)
        
        return jsonify({
            "message": "Application submitted successfully for review",
            "application": application.to_dict()
        }), 200
        
    except ValueError as e:
        return conflict(str(e))


@charity_bp.route("/apply/advance", methods=["POST"])
@role_required("charity")
def advance_step():
    """
    Advance to the next application step.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Step advanced successfully
        400: Cannot advance (already at max step)
    """
    user_id = int(get_jwt_identity())
    
    try:
        application, advanced = CharityService.advance_application_step(user_id)
        
        if advanced:
            return jsonify({
                "message": f"Advanced to step {application.step}",
                "application": application.to_dict()
            }), 200
        else:
            return jsonify({
                "message": "Already at final step",
                "application": application.to_dict()
            }), 200
        
    except ValueError as e:
        return conflict(str(e))


@charity_bp.route("/application", methods=["GET"])
@role_required("charity")
def get_application():
    """
    Get current user's charity application status.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Application details or null if no application
    """
    user_id = int(get_jwt_identity())
    application = CharityService.get_latest_application(user_id)
    
    return jsonify({
        "application": application.to_dict() if application else None
    }), 200


@charity_bp.route("/application/documents", methods=["POST"])
@role_required("charity")
def upload_document():
    """
    Upload a document for the charity application.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Form Data:
        document_type: Type of document (required)
        file: File to upload (required)
        
    Returns:
        201: Document uploaded successfully
        400: Invalid request data
        404: No application found
    """
    user_id = int(get_jwt_identity())
    
    # Check if document_type is provided
    document_type = request.form.get("document_type")
    if not document_type:
        return bad_request("Document type is required")
    
    # Check if file is provided
    if "file" not in request.files:
        return bad_request("File is required")
    
    file = request.files["file"]
    
    # Get application
    application = CharityService.get_latest_application(user_id)
    if not application:
        return not_found("No application found")
    
    # Generate storage path
    from app.utils.file_upload import generate_storage_path
    storage_path = generate_storage_path(
        file_type="documents",
        user_id=user_id,
        filename=file.filename
    )
    
    # Save file
    success, result = save_uploaded_file(file, storage_path)
    
    if not success:
        return bad_request(result)
    
    # Create document record
    try:
        from app.extensions import db
        from app.models import CharityDocument
        
        document = CharityDocument(
            application_id=application.id,
            document_type=document_type,
            file_path=result['path'],
            original_filename=file.filename,
            file_size=result.get('size'),
            mime_type=file.content_type
        )
        
        db.session.add(document)
        db.session.commit()
        
        return jsonify({
            "message": "Document uploaded successfully",
            "document": document.to_dict()
        }), 201
        
    except ValueError as e:
        return bad_request(str(e))


@charity_bp.route("/application/documents", methods=["GET"])
@role_required("charity")
def get_documents():
    """
    Get all documents for the current application.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: List of documents
        404: No application found
    """
    user_id = int(get_jwt_identity())
    
    application = CharityService.get_latest_application(user_id)
    if not application:
        return not_found("No application found")
    
    documents = CharityService.get_application_documents(application.id)
    
    return jsonify({
        "documents": [doc.to_dict() for doc in documents]
    }), 200


# ==================
# Profile Routes
# ==================

@charity_bp.route("/profile", methods=["GET"])
@role_required("charity")
def get_profile():
    """
    Get charity profile.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Charity profile
        404: Charity not found (application may be pending)
    """
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    
    if not charity:
        return not_found("Charity not found. Your application may still be pending.")
    
    return jsonify({"charity": charity.to_dict()}), 200


@charity_bp.route("/profile", methods=["PUT"])
@role_required("charity")
def update_profile():
    """
    Update charity profile.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Request Body (JSON):
        name: New charity name (optional)
        description: New description (optional)
        category: Charity category (optional)
        location: Location/address (optional)
        contact_email: Contact email (optional)
        contact_phone: Contact phone (optional)
        website: Website URL (optional)
        address: Physical address (optional)
        mission: Mission statement (optional)
        goals: Goals/objectives (optional)
        
    Multipart Form Data:
        logo: Logo image file (optional)
        *: Any JSON fields listed above
        
    Returns:
        200: Profile updated successfully
        400: Invalid request data
        404: Charity not found
    """
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    
    if not charity:
        return not_found("Charity not found")
    
    # Handle multipart form data (logo upload)
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form
        files = request.files
    else:
        data = request.get_json()
        files = None
    
    if not data:
        return bad_request("Request body is required")
    
    # Build update kwargs
    updates = {}
    
    # Text fields
    text_fields = [
        'name', 'description', 'category', 'location', 
        'contact_email', 'contact_phone', 'website', 'address',
        'mission', 'goals'
    ]
    
    for field in text_fields:
        if field in data and data[field] is not None:
            value = data[field]
            if isinstance(value, str):
                value = value.strip()
            if field in ('name', 'description') and not value:
                continue  # Skip empty name/description
            updates[field] = value
    
    # Handle logo upload
    if files and 'logo' in files:
        logo_file = files['logo']
        if logo_file and logo_file.filename:
            # Generate storage path for logo
            storage_path = generate_storage_path(
                file_type="logos",
                user_id=user_id,
                filename=logo_file.filename
            )
            
            # Save file
            success, result = save_uploaded_file(logo_file, storage_path)
            
            if success:
                updates['logo_path'] = result['path']
            else:
                return bad_request(f"Logo upload failed: {result}")
    
    if not updates:
        return bad_request("No valid fields to update")
    
    updated_charity = CharityService.update_charity(charity.id, **updates)
    
    return jsonify({
        "message": "Profile updated successfully",
        "charity": updated_charity.to_dict()
    }), 200


# ==================
# Donation Routes
# ==================

@charity_bp.route("/donations", methods=["GET"])
@role_required("charity")
def get_donations():
    """
    Get donations received by the charity.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        limit: Optional limit on number of results
        
    Returns:
        200: List of received donations
        404: Charity not found
    """
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    
    if not charity:
        return not_found("Charity not found")
    
    limit = request.args.get("limit", type=int)
    donations = DonationService.get_donations_by_charity(charity.id, limit=limit)
    
    return jsonify({
        "donations": [d.to_dict(include_donor=True) for d in donations]
    }), 200


# ==================
# Dashboard Routes
# ==================

@charity_bp.route("/dashboard", methods=["GET"])
@role_required("charity")
def dashboard():
    """
    Get charity dashboard with stats and recent donations.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Dashboard data including stats and recent donations
        404: Charity not found
    """
    user_id = int(get_jwt_identity())
    charity = CharityService.get_charity_by_user(user_id)
    
    if not charity:
        return not_found("Charity not found")
    
    # Get statistics
    stats = CharityService.get_charity_stats(charity.id)
    
    # Get recent donations
    recent_donations = DonationService.get_donations_by_charity(charity.id, limit=5)
    
    return jsonify({
        "charity": charity.to_dict(),
        "stats": stats,
        "recent_donations": [d.to_dict(include_donor=True) for d in recent_donations]
    }), 200
