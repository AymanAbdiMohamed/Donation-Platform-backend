"""
Authentication Routes.

Handles user registration, login, and profile retrieval.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from app.services import UserService
from app.errors import bad_request, unauthorized, not_found, conflict

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    
    Request Body:
        email: User's email address (required)
        password: User's password (required)
        role: User role - 'donor' or 'charity' (default: 'donor')
        
    Returns:
        201: User created successfully with access token
        400: Invalid request data
        409: Email already exists
    """
    data = request.get_json()
    
    if not data:
        return bad_request("Request body is required")
    
    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "donor")
    
    # Validation
    if not email:
        return bad_request("Email is required")
    
    if not password:
        return bad_request("Password is required")
    
    if len(password) < 6:
        return bad_request("Password must be at least 6 characters")
    
    # Only allow donor and charity roles for self-registration
    if role not in ("donor", "charity"):
        return bad_request("Role must be 'donor' or 'charity'")
    
    try:
        user = UserService.create_user(email=email, password=password, role=role)
        
        # Create access token (identity must be string)
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role}
        )
        
        return jsonify({
            "message": "User registered successfully",
            "access_token": access_token,
            "user": user.to_dict()
        }), 201
        
    except ValueError as e:
        return conflict(str(e))


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and return JWT token.
    
    Request Body:
        email: User's email address (required)
        password: User's password (required)
        
    Returns:
        200: Login successful with access token
        400: Invalid request data
        401: Invalid credentials
    """
    data = request.get_json()
    
    if not data:
        return bad_request("Request body is required")
    
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    if not email or not password:
        return bad_request("Email and password are required")
    
    user = UserService.authenticate(email, password)
    
    if not user:
        return unauthorized("Invalid email or password")
    
    if not user.is_active:
        return unauthorized("Account is deactivated")
    
    # Create access token (identity must be string)
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": user.to_dict()
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user's profile.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: User profile data
        401: Not authenticated
        404: User not found
    """
    user_id = get_jwt_identity()
    user = UserService.get_by_id(int(user_id))
    
    if not user:
        return not_found("User not found")
    
    return jsonify({"user": user.to_dict()}), 200
