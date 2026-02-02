"""
ALL models in ONE file.
Models: User, Charity, CharityApplication, Donation
"""
from db import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(db.Model):
    """
    User model - donors, charities, and admins.
    
    Roles: 'donor', 'charity', 'admin'
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="donor")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    donations = db.relationship("Donation", backref="donor", lazy="dynamic", foreign_keys="Donation.donor_id")
    charity = db.relationship("Charity", backref="user", uselist=False)

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serialize user (excludes sensitive fields)."""
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class CharityApplication(db.Model):
    """
    Charity application - pending review by admin.
    
    Status: 'pending', 'approved', 'rejected'
    """
    __tablename__ = "charity_applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending")
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    applicant = db.relationship("User", backref="applications")

    def to_dict(self):
        """Serialize application."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None
        }


class Charity(db.Model):
    """
    Approved charity organization.
    """
    __tablename__ = "charities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    donations = db.relationship("Donation", backref="charity", lazy="dynamic")

    def to_dict(self):
        """Serialize charity."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Donation(db.Model):
    """
    Donation record.
    
    amount: stored in cents for precision
    is_anonymous: hide donor info from charity
    is_recurring: monthly donation flag (mock for now)
    """
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)  # cents
    donor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    charity_id = db.Column(db.Integer, db.ForeignKey("charities.id"), nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False)
    is_recurring = db.Column(db.Boolean, default=False)  # Mock: monthly donation
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, include_donor=False):
        """Serialize donation."""
        data = {
            "id": self.id,
            "amount": self.amount,
            "charity_id": self.charity_id,
            "is_anonymous": self.is_anonymous,
            "is_recurring": self.is_recurring,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if include_donor and not self.is_anonymous:
            data["donor_id"] = self.donor_id
        return data
