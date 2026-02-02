"""
JWT authentication and role decorators.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt

jwt = JWTManager()


def role_required(*allowed_roles):
    """
    Decorator to restrict access to specific roles.
    
    Usage:
        @role_required('admin')
        @role_required('donor', 'charity')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role", "")
            
            if user_role not in allowed_roles:
                return jsonify({"error": "Access denied. Insufficient permissions."}), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# JWT error handlers
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token has expired"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"error": "Invalid token"}), 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({"error": "Authorization token required"}), 401
