"""
Authentication Decorators.

Role-based access control decorators for protecting routes.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def role_required(*allowed_roles):
    """
    Decorator to restrict route access to specific user roles.
    
    This decorator should be used AFTER @jwt_required() or can replace it
    as it calls verify_jwt_in_request() internally.
    
    Args:
        *allowed_roles: Variable number of role strings that are allowed access
        
    Returns:
        Decorated function that checks role before executing
        
    Usage:
        @app.route("/admin/users")
        @role_required("admin")
        def get_users():
            ...
        
        @app.route("/content")
        @role_required("admin", "editor")
        def manage_content():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Verify JWT is present and valid
            verify_jwt_in_request()
            
            # Get claims from JWT
            claims = get_jwt()
            user_role = claims.get("role", "")
            
            # Check if user's role is in allowed roles
            if user_role not in allowed_roles:
                return jsonify({
                    "error": "Access denied",
                    "message": f"This resource requires one of these roles: {', '.join(allowed_roles)}"
                }), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """
    Decorator for admin-only routes.
    
    Convenience wrapper around role_required("admin").
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return role_required("admin")(fn)(*args, **kwargs)
    return wrapper


def charity_required(fn):
    """
    Decorator for charity-only routes.
    
    Convenience wrapper around role_required("charity").
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return role_required("charity")(fn)(*args, **kwargs)
    return wrapper


def donor_required(fn):
    """
    Decorator for donor-only routes.
    
    Convenience wrapper around role_required("donor").
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return role_required("donor")(fn)(*args, **kwargs)
    return wrapper
