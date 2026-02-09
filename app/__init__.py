"""
Flask Application Factory.

This module creates and configures the Flask application using the factory pattern.
This allows for easy testing and multiple app configurations.
"""
from flask import Flask

from app.config import Config
from app.extensions import db, jwt, cors, migrate, limiter
from app.errors import register_error_handlers
from app.auth import register_jwt_handlers


def create_app(config_class=Config):
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use (default: Config)
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Validate secrets are not defaults in production
    if not app.config.get('DEBUG') and not app.config.get('TESTING'):
        if app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
            raise RuntimeError("SECRET_KEY must be set via environment variable in production")
        if app.config['JWT_SECRET_KEY'] == 'jwt-secret-key-change-in-production':
            raise RuntimeError("JWT_SECRET_KEY must be set via environment variable in production")
        if app.config.get('CORS_ORIGINS', '*') == '*':
            raise RuntimeError("CORS_ORIGINS must be set to explicit origins in production (not '*')")
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            raise RuntimeError("DATABASE_URL must point to a production database (not SQLite)")

    # Initialize extensions
    _init_extensions(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register JWT handlers
    register_jwt_handlers(jwt)
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


def _init_extensions(app):
    """Initialize Flask extensions."""
    db.init_app(app)
    jwt.init_app(app)
    
    # CORS — parse comma-separated origins from config
    origins = app.config.get("CORS_ORIGINS", "*")
    if origins != "*":
        origins = [o.strip() for o in origins.split(",") if o.strip()]
    cors.init_app(
        app,
        resources={r"/*": {"origins": origins}},
        supports_credentials=True,
    )
    
    migrate.init_app(app, db)
    
    # Rate limiter
    limiter.init_app(app)


def _register_blueprints(app):
    """Register all application blueprints."""
    from app.routes import auth_bp, donor_bp, charity_bp, admin_bp, payment_bp
    from app.routes.health import health_bp
    from app.routes.public import public_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(public_bp)  # No prefix - public routes
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(donor_bp, url_prefix="/donor")
    app.register_blueprint(charity_bp, url_prefix="/charity")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(payment_bp, url_prefix="/payment")
