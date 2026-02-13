#!/usr/bin/env python
"""
Application Entry Point.

Run:
    python run_app.py

CLI:
    flask create-admin --email admin@example.com --password secret
"""

import os
import click

# ── Load environment variables for local development ─────────────
env = os.environ.get("FLASK_ENV", "development")
if env != "production":
    from dotenv import load_dotenv

    env_file = os.path.join(os.path.dirname(__file__), ".env.production")
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✅ Loaded local env from {env_file}")
    else:
        print(f"⚠️  Warning: {env_file} not found. Using system environment variables.")

# ── Flask imports after env loaded ───────────────────────────────
from app import create_app
from app.config import config_by_name

# ── Determine configuration class ───────────────────────────────
config_class = config_by_name.get(env, config_by_name["default"])

# ── Create the Flask application ────────────────────────────────
app = create_app(config_class)

# ── Optional: Debug print to verify M-Pesa / API configuration ──
print("⚡ Flask environment:", env)
print("MPESA_ENV:", app.config.get("MPESA_ENV"))
print("MPESA_CONSUMER_KEY:", app.config.get("MPESA_CONSUMER_KEY"))
print("MPESA_SHORTCODE:", app.config.get("MPESA_SHORTCODE"))
print("MPESA_MOCK_MODE:", app.config.get("MPESA_MOCK_MODE"))

# ── CLI Commands ───────────────────────────────────────────────
@app.cli.command("create-admin")
@click.option("--email", prompt=True, help="Admin email address")
@click.option(
    "--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password"
)
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

# ── Run the server ──────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = env != "production"
    print(f"🚀 Starting server in {env} mode on port {port} (debug={debug})...")
    app.run(host="0.0.0.0", port=port, debug=debug)
