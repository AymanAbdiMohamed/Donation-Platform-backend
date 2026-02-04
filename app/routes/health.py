"""
Health Check Route.

Simple endpoint to verify API is running.
"""
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        200 OK if service is running
    """
    return jsonify({"status": "ok"}), 200
