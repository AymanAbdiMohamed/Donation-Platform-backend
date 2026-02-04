"""
Charity application routes with strict role enforcement.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from db import SessionLocal
from models import User, CharityApplication, Charity
from utils.decorators import charity_only

charity_applications_bp = Blueprint("charity_applications", __name__)


@charity_applications_bp.route("/apply", methods=["POST"])
@jwt_required()
@charity_only
def apply_charity():
    """Submit charity application - charity role only."""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({
            "error": "Invalid request",
            "message": "Request body is required"
        }), 400
    
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    
    if not name:
        return jsonify({
            "error": "Validation error",
            "message": "Charity name is required"
        }), 400
    
    session = SessionLocal()
    try:
        # Check for existing pending application
        existing_pending = session.query(CharityApplication).filter_by(
            user_id=user_id, status="pending"
        ).first()
        
        if existing_pending:
            return jsonify({
                "error": "Application exists",
                "message": "You already have a pending application"
            }), 409
        
        # Check if already approved charity
        existing_charity = session.query(Charity).filter_by(user_id=user_id).first()
        if existing_charity:
            return jsonify({
                "error": "Already approved",
                "message": "You already have an approved charity"
            }), 409
        
        application = CharityApplication(
            user_id=user_id,
            name=name,
            description=description
        )
        
        session.add(application)
        session.commit()
        session.refresh(application)
        
        return jsonify({
            "message": "Application submitted successfully",
            "application": application.to_dict()
        }), 201
        
    except Exception:
        session.rollback()
        return jsonify({
            "error": "Application failed",
            "message": "Unable to submit application"
        }), 500
    finally:
        session.close()


@charity_applications_bp.route("/status", methods=["GET"])
@jwt_required()
@charity_only
def get_application_status():
    """Get charity application status - charity role only."""
    user_id = get_jwt_identity()
    
    session = SessionLocal()
    try:
        application = session.query(CharityApplication).filter_by(
            user_id=user_id
        ).order_by(CharityApplication.created_at.desc()).first()
        
        if not application:
            return jsonify({
                "application": None,
                "message": "No application found"
            }), 200
        
        return jsonify({
            "application": application.to_dict()
        }), 200
        
    finally:
        session.close()