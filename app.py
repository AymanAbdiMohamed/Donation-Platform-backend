"""
Flask application.
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from auth import jwt
from db import init_db
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.charity import charity_bp  # unified charity blueprint

load_dotenv()

app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")

# Initialize extensions
CORS(app)
jwt.init_app(app)

# Initialize database
init_db()

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(charity_bp, url_prefix="/charity")  # unified charity route

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
