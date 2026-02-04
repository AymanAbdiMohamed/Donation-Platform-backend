"""
Charity and CharityApplication Models.

Handles charity organizations and their application process.
"""
from datetime import datetime, timezone

from app.extensions import db


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class CharityApplication(db.Model):
    """
    Charity application for users who want to register as a charity.
    
    Status workflow: pending -> approved/rejected
    """
    __tablename__ = "charity_applications"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending", index=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    applicant = db.relationship("User", back_populates="applications")
    
    # Valid statuses
    VALID_STATUSES = ("pending", "approved", "rejected")
    
    def approve(self):
        """Mark application as approved."""
        self.status = "approved"
        self.reviewed_at = utc_now()
    
    def reject(self, reason=""):
        """
        Mark application as rejected.
        
        Args:
            reason: Rejection reason to provide to applicant
        """
        self.status = "rejected"
        self.rejection_reason = reason
        self.reviewed_at = utc_now()
    
    def is_pending(self):
        """Check if application is still pending."""
        return self.status == "pending"
    
    def to_dict(self):
        """Convert application to dictionary representation."""
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
    
    def __repr__(self):
        return f"<CharityApplication id={self.id} name={self.name} status={self.status}>"


class Charity(db.Model):
    """
    Approved charity organization.
    
    Created when a CharityApplication is approved.
    One-to-one relationship with User (charity role).
    """
    __tablename__ = "charities"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    user = db.relationship("User", back_populates="charity")
    donations = db.relationship(
        "Donation",
        back_populates="charity",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    
    def deactivate(self):
        """Deactivate the charity."""
        self.is_active = False
    
    def activate(self):
        """Reactivate the charity."""
        self.is_active = True
    
    def get_total_donations(self):
        """
        Calculate total donations received.
        
        Returns:
            int: Total donations in cents
        """
        from app.models.donation import Donation
        result = db.session.query(
            db.func.coalesce(db.func.sum(Donation.amount), 0)
        ).filter(Donation.charity_id == self.id).scalar()
        return result or 0
    
    def get_donation_count(self):
        """
        Get number of donations received.
        
        Returns:
            int: Number of donations
        """
        return self.donations.count()
    
    def to_dict(self):
        """Convert charity to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f"<Charity id={self.id} name={self.name}>"
