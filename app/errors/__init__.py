"""
Error Handling Package.

Provides standardized error responses and error handlers.
"""
from app.errors.handlers import register_error_handlers
from app.errors.responses import (
    bad_request,
    unauthorized,
    forbidden,
    not_found,
    conflict,
    internal_error,
)

__all__ = [
    "register_error_handlers",
    "bad_request",
    "unauthorized",
    "forbidden",
    "not_found",
    "conflict",
    "internal_error",
]
