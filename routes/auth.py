"""
Authentication routes blueprint.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from db import SessionLocal
from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "donor")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    session = SessionLocal()
    try:
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "Email already exists"}), 409

        user = User(
            username=email.split("@")[0],
            email=email,
            password=generate_password_hash(password),
            role=role
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        access_token = create_access_token(
            identity=user.id,
            additional_claims={"role": user.role}
        )

        return jsonify({
            "message": "User registered successfully",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
        }), 201

    except Exception:
        session.rollback()
        return jsonify({"error": "Registration failed"}), 500
    finally:
        session.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return JWT."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    session = SessionLocal()
    try:
        user = session.query(User).filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            return jsonify({"error": "Invalid credentials"}), 401

        access_token = create_access_token(
            identity=user.id,
            additional_claims={"role": user.role}
        )

        return jsonify({
            "access_token": access_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
        }), 200

    except Exception:
        return jsonify({"error": "Login failed"}), 500
    finally:
        session.close()
