#!/usr/bin/env python
"""
Application Entry Point.

Run with: python run_app.py
CLI:      flask create-admin --email admin@example.com --password secret
"""
import os
import click
from app import create_app
from app.config import config_by_name

# Get environment (default to development)
env = os.environ.get("FLASK_ENV", "development")
config_class = config_by_name.get(env, config_by_name["default"])

# Create the application
app = create_app(config_class)


# ── CLI Commands ────────────────────────────────────────────────────────

@app.cli.command("create-admin")
@click.option("--email", prompt=True, help="Admin email address")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
def create_admin(email, password):
    """Create an admin user (safe for production — no destructive DB ops)."""
    from app.services import UserService

    if len(password) < 6:
        click.echo("Error: Password must be at least 6 characters.", err=True)
        raise SystemExit(1)

    try:
        user = UserService.create_user(email=email, password=password, role="admin")
        click.echo(f"Admin user created: {user.email} (id={user.id})")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

if __name__ == "__main__":
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))
    debug = env == "development"
    
    print(f"Starting server in {env} mode on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=debug)
