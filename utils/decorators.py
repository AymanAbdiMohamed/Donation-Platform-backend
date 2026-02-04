"""
Role-based access control decorators.
Implements @role_required for protecting routes by user role,
while retaining convenience decorators for specific roles.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def role_required(*allowed_roles):
    """
    Decorator to restrict access to specific roles.
    
    Args:
        allowed_roles: One or more allowed roles (e.g., 'admin', 'charity', 'donor')
    
    Returns:
        403 JSON error if user role does not match required roles.
        401 JSON error if user is not authenticated.
    
    Usage:
        @role_required('admin')
        def admin_only_route():
            ...
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


# Convenience decorators for single roles
def charity_only(fn):
    """Decorator for charity-only endpoints."""
    return role_required("charity")(fn)


def admin_only(fn):
    """Decorator for admin-only endpoints."""
    return role_required("admin")(fn)


def donor_only(fn):
    """Decorator for donor-only endpoints."""
    return role_required("donor")(fn)
