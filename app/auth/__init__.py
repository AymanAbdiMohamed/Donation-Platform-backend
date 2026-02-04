"""
Authentication Package.

Provides JWT authentication and role-based access control.
"""
from app.auth.decorators import role_required, admin_required, charity_required, donor_required
from app.auth.handlers import register_jwt_handlers

__all__ = [
    "role_required",
    "admin_required",
    "charity_required",
    "donor_required",
    "register_jwt_handlers",
]
