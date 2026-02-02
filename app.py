"""
Flask app + route registration.
"""
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from db import db
from auth import jwt
from routes import api

migrate = Migrate()


def create_app():
    """Create and configure Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS for frontend
    CORS(app, origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register routes
    app.register_blueprint(api, url_prefix="/api")

    # Create tables (dev only - use migrations in production)
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
