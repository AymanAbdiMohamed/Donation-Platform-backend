"""
Flask Extensions.

Centralized initialization of Flask extensions.
Extensions are initialized without an app instance and bound later via init_app().
"""
import os

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_apscheduler import APScheduler

# Database ORM
db = SQLAlchemy()

# JWT Authentication
jwt = JWTManager()

# Cross-Origin Resource Sharing
cors = CORS()

# Database Migrations
migrate = Migrate()

# Rate Limiter
# RATELIMIT_STORAGE_URI should be set to a Redis URL in production so that
# counters are shared across all Gunicorn worker processes.  Falls back to
# in-process memory for local development (single-process only).
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # No default; applied per-blueprint/route
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)

# Task Scheduler
scheduler = APScheduler()
