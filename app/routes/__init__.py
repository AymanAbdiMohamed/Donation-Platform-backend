"""
Routes Package.

All API route blueprints are registered here.
"""
from app.routes.auth import auth_bp
from app.routes.donor import donor_bp
from app.routes.charity import charity_bp
from app.routes.admin import admin_bp
from app.routes.payment import payment_bp

__all__ = [
    "auth_bp",
    "donor_bp",
    "charity_bp",
    "admin_bp",
    "payment_bp",
]
