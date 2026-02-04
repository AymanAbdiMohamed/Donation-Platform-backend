"""
Database configuration using Flask-SQLAlchemy.
"""
import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

# Initialize SQLAlchemy
db = SQLAlchemy()

def get_database_url():
    """Get database URL from environment variables."""
    # Use SQLite for testing if PostgreSQL vars not set
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB = os.getenv("POSTGRES_DB")

    if all([POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]):
        return (
            f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@{POSTGRES_HOST}/{POSTGRES_DB}"
        )
    else:
        return "sqlite:///test.db"

def init_db(app):
    """Initialize database with Flask app."""
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()

