"""
Seed script to create admin user.
"""
import hashlib
from models import User
from db import SessionLocal

# Hash password using hashlib
password = "admin123"
hashed_password = hashlib.sha256(password.encode()).hexdigest()

# Create session
session = SessionLocal()

# Create admin user
admin = User(
    username="admin",
    email="admin@example.com",
    password=hashed_password,
    role="ADMIN"
)

session.add(admin)
session.commit()
session.close()

print("Admin user created")
