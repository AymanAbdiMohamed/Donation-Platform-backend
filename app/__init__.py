"""
Flask Application Factory.

This module creates and configures the Flask application using the factory pattern.
This allows for easy testing and multiple app configurations.
"""
import os
import sys

from flask import Flask

from app.config import Config
from app.extensions import db, jwt, cors, migrate, limiter
from app.errors import register_error_handlers
from app.auth import register_jwt_handlers


def _is_cli_context() -> bool:
    """
    Detect if the app is being created for a Flask CLI command.
    
    Flask CLI commands (flask db, flask shell, etc.) should not enforce
    production-level security checks because they run in a different context
    than the web server.
    
    Detection methods:
    1. FLASK_CLI_MODE env var explicitly set
    2. Running under flask CLI (argv inspection)
    3. Running via python -m flask
    """
    # Explicit override via environment variable
    if os.environ.get("FLASK_CLI_MODE", "").lower() in ("1", "true", "yes"):
        return True
    
    # Detect flask CLI commands from sys.argv
    if len(sys.argv) > 0:
        script = os.path.basename(sys.argv[0])
        # Common CLI entry points
        if script == "flask" or script.endswith("flask"):
            return True
        # Running via python -m flask
        if "flask" in sys.argv or any("flask" in arg for arg in sys.argv[:3]):
            return True
        # Direct invocation of migration scripts
        if script in ("seed_admin.py", "seed_db.py"):
            return True
    
    return False


def _is_production_server() -> bool:
    """
    Determine if we're running as a production web server.
    
    Returns True ONLY when:
    1. Not in CLI mode
    2. Not in DEBUG mode
    3. Not in TESTING mode
    4. FLASK_ENV is 'production' OR running under gunicorn/uwsgi
    
    This ensures strict security checks apply only when serving real traffic.
    """
    if _is_cli_context():
        return False
    
    # Explicitly disabled
    if os.environ.get("DEBUG", "false").lower() in ("1", "true"):
        return False
    if os.environ.get("TESTING", "false").lower() in ("1", "true"):
        return False
    
    # Check for production indicators
    flask_env = os.environ.get("FLASK_ENV", "development")
    if flask_env == "production":
        return True
    
    # Detect WSGI servers (gunicorn, uwsgi)
    if len(sys.argv) > 0:
        script = os.path.basename(sys.argv[0])
        if script in ("gunicorn", "uwsgi"):
            return True
    
    return False


def create_app(config_class=Config):
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use (default: Config)
    
    Returns:
        Configured Flask application instance
        
    Security:
        Production-level security checks (SECRET_KEY, JWT_SECRET_KEY, 
        CORS_ORIGINS, DATABASE_URL) are enforced ONLY when running 
        as a production web server (gunicorn/uwsgi with FLASK_ENV=production).
        
        Flask CLI commands (flask db, flask shell) run with relaxed checks
        to allow local development and CI/CD pipelines to function.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Determine runtime context
    is_cli = _is_cli_context()
    is_production = _is_production_server()
    
    # Log context for debugging
    if app.config.get("DEBUG") or is_cli:
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logger.addHandler(handler)
        logger.debug(
            "App context: CLI=%s, Production=%s, FLASK_ENV=%s",
            is_cli, is_production, os.environ.get("FLASK_ENV", "development")
        )

    # Enforce strict security checks ONLY in production server mode
    if is_production:
        _validate_production_config(app.config)
    elif not is_cli:
        # Development server mode - allow wildcard CORS
        app.config["CORS_ORIGINS"] = app.config.get("CORS_ORIGINS", "*")
    # CLI mode - use whatever config is provided, no extra validation

    # Initialize extensions
    _init_extensions(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register JWT handlers
    register_jwt_handlers(jwt)
    
    # Security headers (only apply to HTTP responses, not CLI)
    if not is_cli:
        @app.after_request
        def set_security_headers(response):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            if is_production:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response
    
    # Validate M-Pesa configuration at startup (warn only, don't crash)
    # Skip for CLI commands to avoid unnecessary warnings
    if not is_cli:
        with app.app_context():
            config_class.validate_mpesa()
    
    return app


def _validate_production_config(config):
    """
    Validate configuration for production deployment.
    
    Raises RuntimeError if any security-critical configuration is missing
    or set to insecure defaults.
    """
    errors = []
    
    if config.get("SECRET_KEY") == "dev-secret-key-change-in-production":
        errors.append("SECRET_KEY must be set via environment variable in production")
    
    if config.get("JWT_SECRET_KEY") == "jwt-secret-key-change-in-production":
        errors.append("JWT_SECRET_KEY must be set via environment variable in production")
    
    cors_origins = config.get("CORS_ORIGINS", "*")
    if cors_origins == "*" or not cors_origins:
        errors.append("CORS_ORIGINS must be set to explicit origins in production (not '*')")
    
    db_uri = config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite"):
        errors.append("DATABASE_URL must point to a production database (not SQLite)")
    
    if errors:
        raise RuntimeError(
            "Production configuration validation failed:\n" + 
            "\n".join(f"  - {e}" for e in errors)
        )


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
    from app.routes.donations_api import donations_api_bp
    from app.routes.stories import stories_bp
    from app.routes.beneficiaries import beneficiaries_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(public_bp)  # No prefix - public routes
    app.register_blueprint(stories_bp)  # No prefix - has both public and charity routes
    app.register_blueprint(beneficiaries_bp)  # No prefix - charity routes under /charity/
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(donor_bp, url_prefix="/donor")
    app.register_blueprint(charity_bp, url_prefix="/charity")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(payment_bp, url_prefix="/api/mpesa")
    app.register_blueprint(donations_api_bp, url_prefix="/api/donations")
