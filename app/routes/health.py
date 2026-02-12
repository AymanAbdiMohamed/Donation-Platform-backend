"""
Health Check Route.

Simple endpoint to verify API is running and check service dependencies.
"""
from flask import Blueprint, jsonify

from app.services import PaymentService
from app.extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        200 OK if service is running
    """
    return jsonify({"status": "ok"}), 200


@health_bp.route("/health/database", methods=["GET"])
def database_health():
    """
    Database connectivity check.
    
    Returns:
        200: Database is accessible
        500: Database connection failed
    """
    try:
        # Simple query to test database connectivity
        result = db.engine.execute(db.text("SELECT 1"))
        result.close()
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "database": "disconnected",
            "error": str(e)
        }), 500


@health_bp.route("/health/mpesa", methods=["GET"])  
def mpesa_health():
    """
    M-Pesa service connectivity check.
    
    Tests M-Pesa configuration and ability to obtain access tokens.
    Useful for debugging M-Pesa integration issues.
    
    Returns:
        200: M-Pesa configured and accessible
        503: M-Pesa not configured or inaccessible  
    """
    try:
        # Test M-Pesa configuration and connection
        test_result = PaymentService.test_connection()
        
        if test_result["success"]:
            return jsonify({
                "status": "healthy",
                "mpesa": "connected",
                "environment": test_result.get("environment"),
                "message": test_result.get("message")
            })
        else:
            return jsonify({
                "status": "unhealthy",
                "mpesa": "disconnected", 
                "error": test_result.get("error")
            }), 503
            
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "mpesa": "error",
            "error": str(e)
        }), 503
