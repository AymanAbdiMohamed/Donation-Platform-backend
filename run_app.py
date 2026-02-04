#!/usr/bin/env python
"""
Application Entry Point.

Run with: python run.py
"""
import os
from app import create_app
from app.config import config_by_name

# Get environment (default to development)
env = os.environ.get("FLASK_ENV", "development")
config_class = config_by_name.get(env, config_by_name["default"])

# Create the application
app = create_app(config_class)

if __name__ == "__main__":
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))
    debug = env == "development"
    
    print(f"Starting server in {env} mode on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=debug)
