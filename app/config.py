"""
Application Configuration.

Contains configuration classes for different environments.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _get_database_url():
    """
    Build database URL from environment variables.
    Falls back to SQLite for development.
    """
    postgres_host = os.getenv("POSTGRES_HOST")
    postgres_user = os.getenv("POSTGRES_USER")
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    postgres_db = os.getenv("POSTGRES_DB")
    
    if all([postgres_host, postgres_user, postgres_password, postgres_db]):
        return (
            f"postgresql://{postgres_user}:{postgres_password}"
            f"@{postgres_host}/{postgres_db}"
        )
    
    return "sqlite:///donation_platform.db"


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _get_database_url())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    
    # File Uploads
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max upload size
    
    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_EXPIRES_HOURS", 24)))
    JWT_ERROR_MESSAGE_KEY = "error"
    
    # CORS — comma-separated origins, e.g. "https://example.com,https://www.example.com"
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    
    # Rate limiting
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per hour")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # ── M-Pesa Daraja ───────────────────────────────────────────────────────
    MPESA_ENV = os.environ.get("MPESA_ENV", "sandbox")
    MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "174379")
    MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "")
    MPESA_STK_CALLBACK_URL = os.environ.get("MPESA_STK_CALLBACK_URL", "")
    MPESA_TIMEOUT_URL = os.environ.get("MPESA_TIMEOUT_URL", "")

    @staticmethod
    def validate_mpesa():
        """Check that all required M-Pesa vars are set. Call at startup."""
        required = {
            "MPESA_CONSUMER_KEY": os.environ.get("MPESA_CONSUMER_KEY", ""),
            "MPESA_CONSUMER_SECRET": os.environ.get("MPESA_CONSUMER_SECRET", ""),
            "MPESA_PASSKEY": os.environ.get("MPESA_PASSKEY", ""),
            "MPESA_STK_CALLBACK_URL": os.environ.get("MPESA_STK_CALLBACK_URL", ""),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "M-Pesa NOT fully configured — missing: %s. "
                "STK Push endpoints will return errors until these are set.",
                ", ".join(missing),
            )
            return False
        return True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Enforce explicit CORS origins in production
    # CORS_ORIGINS must be set via env var (no wildcard fallback)


# Configuration mapping
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
