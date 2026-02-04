"""
Routes package.
"""
from .auth import auth_bp
from .admin import admin_bp
from .charity import charity_bp

__all__ = ["auth_bp", "admin_bp", "charity_bp"]
