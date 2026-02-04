"""
JWT Error Handlers.

Custom error handlers for JWT-related errors.
"""
from flask import jsonify


def register_jwt_handlers(jwt):
    """
    Register custom JWT error handlers.
    
    Args:
        jwt: JWTManager instance to register handlers with
    """
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Handle expired tokens."""
        return jsonify({
            "error": "Token expired",
            "message": "Your session has expired. Please login again."
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Handle invalid tokens."""
        return jsonify({
            "error": "Invalid token",
            "message": "The provided token is invalid."
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Handle missing tokens."""
        return jsonify({
            "error": "Authorization required",
            "message": "Please provide a valid access token."
        }), 401
    
    @jwt.token_in_blocklist_loader
    def check_token_blocklist(jwt_header, jwt_payload):
        """
        Check if token is in blocklist (for logout functionality).
        
        Currently returns False as blocklist is not implemented.
        To implement, add token JTI to a blocklist (Redis, DB, etc.) on logout.
        """
        # TODO: Implement token blocklist for logout support
        return False
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """Handle revoked tokens."""
        return jsonify({
            "error": "Token revoked",
            "message": "This token has been revoked."
        }), 401
    
    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        """Handle requests requiring fresh tokens."""
        return jsonify({
            "error": "Fresh token required",
            "message": "Please login again to perform this action."
        }), 401
