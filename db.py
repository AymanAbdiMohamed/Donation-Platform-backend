"""
Database connection using SQLAlchemy.
Supports both SQLite (for development) and PostgreSQL (for production).
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
