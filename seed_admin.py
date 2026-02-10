#!/usr/bin/env python
"""
Admin Seed Script.

Creates the initial admin user for production deployments.
This script is safe to run multiple times - it will not create duplicates.

Usage:
    python seed_admin.py                           # Uses defaults or env vars
    python seed_admin.py --email admin@example.com # Override email
    
Environment Variables:
    ADMIN_EMAIL    - Admin email (default: admin@sheneeds.org)
    ADMIN_PASSWORD - Admin password (default: auto-generated)
    
On Render:
    1. Go to your backend service dashboard
    2. Click "Shell" tab
    3. Run: python seed_admin.py
"""
import os
import sys
import secrets
import argparse

# Mark as CLI mode to bypass production security checks
os.environ["FLASK_CLI_MODE"] = "1"

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User


def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def seed_admin(email: str = None, password: str = None, username: str = None) -> dict:
    """
    Create or update the admin user.
    
    Args:
        email: Admin email address
        password: Admin password (auto-generated if not provided)
        username: Admin username
        
    Returns:
        dict with status and credentials
    """
    # Use env vars as defaults
    email = email or os.environ.get("ADMIN_EMAIL", "admin@sheneeds.org")
    password = password or os.environ.get("ADMIN_PASSWORD")
    username = username or email.split("@")[0]
    
    # Check if admin already exists
    existing = User.query.filter_by(email=email).first()
    
    if existing:
        if existing.role != "admin":
            # Upgrade existing user to admin
            existing.role = "admin"
            db.session.commit()
            return {
                "status": "upgraded",
                "message": f"Upgraded existing user '{email}' to admin role",
                "email": email,
                "password": None,  # Not changed
            }
        return {
            "status": "exists",
            "message": f"Admin user '{email}' already exists",
            "email": email,
            "password": None,  # Not revealed
        }
    
    # Generate password if not provided
    generated_password = not password
    if not password:
        password = generate_secure_password()
    
    # Create new admin user
    admin = User(email=email, role="admin", username=username)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    
    return {
        "status": "created",
        "message": f"Created new admin user '{email}'",
        "email": email,
        "password": password if generated_password else "[provided by user]",
        "generated": generated_password,
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create or update admin user for SheNeeds Donation Platform"
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Admin email address (default: admin@sheneeds.org or ADMIN_EMAIL env var)"
    )
    parser.add_argument(
        "--password",
        type=str,
        help="Admin password (default: auto-generated or ADMIN_PASSWORD env var)"
    )
    parser.add_argument(
        "--username",
        type=str,
        help="Admin username (default: derived from email)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SheNeeds Admin User Setup")
    print("=" * 60)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        result = seed_admin(
            email=args.email,
            password=args.password,
            username=args.username,
        )
        
        print()
        print(f"Status: {result['status'].upper()}")
        print(f"Message: {result['message']}")
        print()
        
        if result["status"] == "created":
            print("=" * 60)
            print("🔐 ADMIN CREDENTIALS (SAVE THESE!)")
            print("=" * 60)
            print(f"   Email:    {result['email']}")
            print(f"   Password: {result['password']}")
            print()
            if result.get("generated"):
                print("⚠️  This password was auto-generated and will NOT be shown again!")
                print("   Change it immediately after first login.")
            print("=" * 60)
        elif result["status"] == "exists":
            print("No changes made. To reset the password, you can:")
            print("1. Use the password reset flow (if email is configured)")
            print("2. Use Flask shell: flask shell → user.set_password('new')")
        elif result["status"] == "upgraded":
            print("User was upgraded to admin role.")
            print("Existing password was not changed.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
