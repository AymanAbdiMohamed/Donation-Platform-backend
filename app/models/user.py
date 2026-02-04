"""
User Model.

Handles user data including authentication credentials and role management.
"""
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class User(db.Model):
    """
    User model for donors, charities, and admins.
    
    Roles:
        - donor: Can browse charities and make donations
        - charity: Can manage charity profile and view received donations
        - admin: Can manage platform, approve/reject applications
    """
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="donor")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    donations = db.relationship(
        "Donation",
        back_populates="donor",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    charity = db.relationship(
        "Charity",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    applications = db.relationship(
        "CharityApplication",
        back_populates="applicant",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    # Valid roles
    VALID_ROLES = ("donor", "charity", "admin")
    
    def __init__(self, email, role="donor", username=None, **kwargs):
        """
        Initialize a new user.
        
        Args:
            email: User's email address
            role: User's role (donor, charity, admin)
            username: Optional username (defaults to email prefix)
        """
        super().__init__(**kwargs)
        self.email = email
        self.role = role if role in self.VALID_ROLES else "donor"
        self.username = username or email.split("@")[0]
    
    def set_password(self, password):
        """
        Hash and store password.
        
        Args:
            password: Plain text password to hash
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Verify password against stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            bool: True if password matches
        """
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_email=True):
        """
        Convert user to dictionary representation.
        
        Args:
            include_email: Whether to include email in response
            
        Returns:
            dict: User data
        """
        data = {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_email:
            data["email"] = self.email
        
        return data
    
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == "admin"
    
    def is_charity(self):
        """Check if user has charity role."""
        return self.role == "charity"
    
    def is_donor(self):
        """Check if user has donor role."""
        return self.role == "donor"
    
    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"
