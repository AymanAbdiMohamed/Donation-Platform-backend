"""
Role-based access control decorators.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def require_role(*allowed_roles):
    """
    Decorator to restrict access to specific roles.
    Returns clean error messages for unauthorized access.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get("role", "")
                
                if user_role not in allowed_roles:
                    return jsonify({
                        "error": "Access denied",
                        "message": f"This action requires {' or '.join(allowed_roles)} role"
                    }), 403
                
                return fn(*args, **kwargs)
            except Exception:
                return jsonify({
                    "error": "Authentication required",
                    "message": "Please login to access this resource"
                }), 401
        return wrapper
    return decorator


def charity_only(fn):
    """Decorator for charity-only endpoints."""
    return require_role("charity")(fn)


def admin_only(fn):
    """Decorator for admin-only endpoints."""
    return require_role("admin")(fn)


def donor_only(fn):
    """Decorator for donor-only endpoints."""
    return require_role("donor")(fn)