"""
Error Handlers.

Global error handlers for the Flask application.
"""
from flask import jsonify


def register_error_handlers(app):
    """
    Register global error handlers with the Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        return jsonify({
            "error": "Bad request",
            "message": str(error.description) if hasattr(error, 'description') else "Invalid request"
        }), 400
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication required"
        }), 401
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        return jsonify({
            "error": "Forbidden",
            "message": "You do not have permission to access this resource"
        }), 403
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            "error": "Not found",
            "message": "The requested resource was not found"
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            "error": "Method not allowed",
            "message": "The HTTP method is not allowed for this endpoint"
        }), 405
    
    @app.errorhandler(409)
    def handle_conflict(error):
        return jsonify({
            "error": "Conflict",
            "message": str(error.description) if hasattr(error, 'description') else "Resource conflict"
        }), 409
    
    @app.errorhandler(422)
    def handle_unprocessable(error):
        return jsonify({
            "error": "Unprocessable entity",
            "message": "The request data could not be processed"
        }), 422
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        return jsonify({
            "error": "Too many requests",
            "message": "Rate limit exceeded. Please try again later."
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        # Log the error for debugging (in production, use proper logging)
        app.logger.error(f"Internal error: {error}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions."""
        app.logger.error(f"Unhandled exception: {error}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500
