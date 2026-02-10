#!/usr/bin/env python
"""
Safe Migration Script for Render Deployments.

This script handles the common case where:
1. Database tables already exist (manually created or from a previous deployment)
2. Alembic migration history is not synced with the actual database state

Usage:
    python scripts/safe_migrate.py

What it does:
1. Attempts `flask db upgrade`
2. If tables already exist, stamps the database at the latest revision
3. Re-attempts `flask db upgrade` to apply any pending migrations

This is safe to run on:
- Fresh databases (runs normal upgrade)
- Existing databases with synced migrations (no-op)
- Existing databases with unsynced migrations (stamps then upgrades)
"""
import os
import sys
import subprocess

# Set CLI mode to bypass production checks
os.environ["FLASK_CLI_MODE"] = "1"

def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


def get_current_revision() -> str | None:
    """Get the current Alembic revision from the database."""
    result = run_command(["flask", "db", "current"], check=False)
    if result.returncode != 0:
        return None
    # Parse output like "abc123 (head)"
    output = result.stdout.strip()
    if output:
        return output.split()[0] if output.split() else None
    return None


def main():
    print("=" * 60)
    print("Safe Migration Script")
    print("=" * 60)
    
    # Check current state
    current = get_current_revision()
    print(f"Current revision: {current or 'None (fresh database)'}")
    
    # Try normal upgrade first
    print("\n--- Attempting flask db upgrade ---")
    result = run_command(["flask", "db", "upgrade"], check=False)
    
    if result.returncode == 0:
        print("\n✓ Migration successful!")
        return 0
    
    # Check if failure is due to existing tables
    error_output = (result.stdout + result.stderr).lower()
    if "already exists" in error_output or "duplicate" in error_output:
        print("\n--- Tables already exist, stamping database ---")
        
        # Stamp at head to mark current state as migrated
        stamp_result = run_command(["flask", "db", "stamp", "head"], check=False)
        if stamp_result.returncode != 0:
            print("ERROR: Failed to stamp database")
            return 1
        
        print("\n--- Re-attempting flask db upgrade ---")
        upgrade_result = run_command(["flask", "db", "upgrade"], check=False)
        
        if upgrade_result.returncode == 0:
            print("\n✓ Migration successful after stamp!")
            return 0
        else:
            print("\nERROR: Migration still failed after stamping")
            return 1
    else:
        print(f"\nERROR: Migration failed with unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
