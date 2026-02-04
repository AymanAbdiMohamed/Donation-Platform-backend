"""
SQLAlchemy models.
"""
from datetime import datetime, timezone

from db import db


def utc_now():
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# =========================
# User Model
# =========================
class User(db.Model):
    """User model - donors, charities, and admins."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # donor, charity, admin

    # Relationships
    donations = db.relationship("Donation", back_populates="donor")
    charity = db.relationship("Charity", back_populates="user", uselist=False)
    applications = db.relationship("CharityApplication", back_populates="applicant")

    def __repr__(self):
        return f"<User id={self.id} username={self.username} role={self.role}>"


# =========================
# Charity Application Model
# =========================
class CharityApplication(db.Model):
    """Charity application request."""
    __tablename__ = "charity_applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    rejection_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=utc_now)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    applicant = db.relationship("User", back_populates="applications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


# =========================
# Charity Model
# =========================
class Charity(db.Model):
    """Approved charity organization."""
    __tablename__ = "charities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    user = db.relationship("User", back_populates="charity")
    donations = db.relationship("Donation", back_populates="charity")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =========================
# Donation Model
# =========================
class Donation(db.Model):
    """
    Donation record.
    Amount stored in cents.
    """
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    charity_id = db.Column(db.Integer, db.ForeignKey("charities.id"), nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False)
    is_recurring = db.Column(db.Boolean, default=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    donor = db.relationship("User", back_populates="donations")
    charity = db.relationship("Charity", back_populates="donations")

    def to_dict(self, include_donor=False):
        data = {
            "id": self.id,
            "amount": self.amount,
            "charity_id": self.charity_id,
            "is_anonymous": self.is_anonymous,
            "is_recurring": self.is_recurring,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_donor and not self.is_anonymous:
            data["donor_id"] = self.donor_id

        return data
