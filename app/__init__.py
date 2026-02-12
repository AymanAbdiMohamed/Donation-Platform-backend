"""
Flask Application Factory.

Creates and configures the Flask application using the factory pattern.
Supports multiple environments (development, testing, production) with
proper CORS, JWT, DB, rate limiting, and security headers.
"""
import os
import sys
import logging

from flask_cors import CORS

from flask import Flask
from app.config import Config
from app.extensions import db, jwt, cors, migrate, limiter, scheduler
from app.errors import register_error_handlers
from app.auth import register_jwt_handlers
from app.services.scheduler_service import SchedulerService


def _is_cli_context() -> bool:
    """Detect if running in Flask CLI or script mode."""
    if os.environ.get("FLASK_CLI_MODE", "").lower() in ("1", "true", "yes"):
        return True
    if len(sys.argv) > 0:
        script = os.path.basename(sys.argv[0])
        if script == "flask" or script.endswith("flask"):
            return True
        if "flask" in sys.argv or any("flask" in arg for arg in sys.argv[:3]):
            return True
        if script in ("seed_admin.py", "seed_db.py"):
            return True
    return False


def _is_production_server() -> bool:
    """Detect if running as a production web server (gunicorn/uwsgi)."""
    if _is_cli_context():
        return False
    if os.environ.get("DEBUG", "false").lower() in ("1", "true"):
        return False
    if os.environ.get("TESTING", "false").lower() in ("1", "true"):
        return False
    flask_env = os.environ.get("FLASK_ENV", "development")
    if flask_env == "production":
        return True
    if len(sys.argv) > 0:
        script = os.path.basename(sys.argv[0])
        if script in ("gunicorn", "uwsgi"):
            return True
    return False


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    is_cli = _is_cli_context()
    is_production = _is_production_server()

    # Debug logging for context
    if app.config.get("DEBUG") or is_cli:
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

    # Production configuration validation
    if is_production:
        _validate_production_config(app.config)
    elif not is_cli:
        # Development server mode: allow wildcard CORS if not set
        app.config["CORS_ORIGINS"] = app.config.get("CORS_ORIGINS", "*")

    # Initialize extensions
    _init_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register JWT handlers
    register_jwt_handlers(jwt)

    # Security headers (skip for CLI)
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

    # Validate M-Pesa config (warn only)
    if not is_cli:
        with app.app_context():
            config_class.validate_mpesa()

    return app


def _validate_production_config(config):
    """Validate security-critical config for production."""
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
    """Initialize Flask extensions (DB, JWT, CORS, Migrate, Limiter)."""
    db.init_app(app)
    jwt.init_app(app)

    # CORS configuration
    origins = app.config.get("CORS_ORIGINS", "*")
    if origins != "*":
        origins = [o.strip() for o in origins.split(",") if o.strip()]
    CORS(
        app,
        resources={r"/*": {"origins": origins}},
        supports_credentials=True,
    )

    migrate.init_app(app, db)
    limiter.init_app(app)

    # Initialize Scheduler
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        scheduler.init_app(app)
        scheduler.start()
        
        # Add recurring donation job
        scheduler.add_job(
            id="process_recurring_donations",
            func=SchedulerService.process_recurring_donations,
            trigger="interval",
            hours=24,  # Run once daily
            replace_existing=True
        )


def _register_blueprints(app):
    """Register all blueprints."""
    from app.routes import auth_bp, donor_bp, charity_bp, admin_bp, payment_bp
    from app.routes.payment_frontend import payment_bp as frontend_payment_bp  # new
    from app.routes.health import health_bp
    from app.routes.public import public_bp
    from app.routes.donations_api import donations_api_bp
    from app.routes.stories import stories_bp
    from app.routes.beneficiaries import beneficiaries_bp

    # Public & API blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(public_bp)          # Public routes
    app.register_blueprint(stories_bp)         # Public + charity
    app.register_blueprint(beneficiaries_bp)   # Charity routes

    # Auth & user routes
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(donor_bp, url_prefix="/donor")
    app.register_blueprint(charity_bp, url_prefix="/charity")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Payment / Donations API
    app.register_blueprint(payment_bp, url_prefix="/api/mpesa")
    app.register_blueprint(donations_api_bp, url_prefix="/api/donations")
