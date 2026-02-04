"""
SQLAlchemy models.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from db import Base


def utc_now():
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# =========================
# User Model
# =========================
class User(Base):
    """User model - donors, charities, and admins."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False)  # donor, charity, admin

    # Relationships
    donations = relationship("Donation", back_populates="donor")
    charity = relationship("Charity", back_populates="user", uselist=False)
    applications = relationship("CharityApplication", back_populates="applicant")

    def __repr__(self):
        return f"<User id={self.id} username={self.username} role={self.role}>"


# =========================
# Charity Application Model
# =========================
class CharityApplication(Base):
    """Charity application request."""
    __tablename__ = "charity_applications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    applicant = relationship("User", back_populates="applications")

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
class Charity(Base):
    """Approved charity organization."""
    __tablename__ = "charities"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    user = relationship("User", back_populates="charity")
    donations = relationship("Donation", back_populates="charity")

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
class Donation(Base):
    """
    Donation record.
    Amount stored in cents.
    """
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True)
    amount = Column(Integer, nullable=False)
    donor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    charity_id = Column(Integer, ForeignKey("charities.id"), nullable=False)
    is_anonymous = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    donor = relationship("User", back_populates="donations")
    charity = relationship("Charity", back_populates="donations")

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
