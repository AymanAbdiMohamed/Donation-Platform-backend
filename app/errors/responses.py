"""
Standardized Error Responses.

Provides consistent error response format across the API.
"""
from flask import jsonify


def error_response(status_code, error, message=None):
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error: Short error description
        message: Detailed error message (optional)
        
    Returns:
        tuple: (Response, status_code)
    """
    response = {"error": error}
    if message:
        response["message"] = message
    return jsonify(response), status_code


def bad_request(message="Invalid request data"):
    """
    400 Bad Request response.
    
    Use when request data is invalid or missing required fields.
    """
    return error_response(400, "Bad request", message)


def unauthorized(message="Authentication required"):
    """
    401 Unauthorized response.
    
    Use when authentication is required but not provided or invalid.
    """
    return error_response(401, "Unauthorized", message)


def forbidden(message="You do not have permission to access this resource"):
    """
    403 Forbidden response.
    
    Use when user is authenticated but lacks required permissions.
    """
    return error_response(403, "Forbidden", message)


def not_found(message="Resource not found"):
    """
    404 Not Found response.
    
    Use when the requested resource does not exist.
    """
    return error_response(404, "Not found", message)


def conflict(message="Resource already exists"):
    """
    409 Conflict response.
    
    Use when resource already exists or state prevents operation.
    """
    return error_response(409, "Conflict", message)


def internal_error(message="An unexpected error occurred"):
    """
    500 Internal Server Error response.
    
    Use when an unexpected server error occurs.
    """
    return error_response(500, "Internal server error", message)
