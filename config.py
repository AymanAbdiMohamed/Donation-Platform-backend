"""
Application configuration - Development only.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Development configuration."""
    
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Database - SQLite for dev, PostgreSQL via DATABASE_URL for production
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", 
        "sqlite:///donation_platform.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
