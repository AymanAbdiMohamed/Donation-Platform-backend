"""
Role-based access control decorators.

BE2 Day 2 - Role Protection:
Implements @role_required decorator for protecting routes by user role.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def role_required(role_name):
    """
    Decorator to restrict route access to a specific role.
    
    Args:
        role_name: The required role (e.g., 'admin', 'charity', 'donor')
    
    Returns:
        403 JSON error if user role does not match required role.
    
    Usage:
        @role_required('admin')
        def admin_only_route():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role", "")
            
            if user_role != role_name:
                return jsonify({
                    "error": "Unauthorized. Required role: {}".format(role_name)
                }), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator
