"""
Donation Model.

Handles donation records between donors and charities.

A donation is created with status PENDING when an STK Push is initiated.
The callback handler updates it to SUCCESS or FAILED.
"""
from datetime import datetime, timezone

from app.extensions import db


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class DonationStatus:
    """Enum-like constants for donation status."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Donation(db.Model):
    """
    Donation record.
    
    Amount is stored in cents to avoid floating-point issues.
    Platform is KES-only: KES 500 = 50000 cents.
    """
    __tablename__ = "donations"
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)  # Amount in cents
    donor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    charity_id = db.Column(
        db.Integer,
        db.ForeignKey("charities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    is_anonymous = db.Column(db.Boolean, default=False)
    is_recurring = db.Column(db.Boolean, default=False)
    message = db.Column(db.Text, nullable=True)

    # ── M-Pesa tracking fields ──────────────────────────────────────────
    phone_number = db.Column(db.String(15), nullable=True)
    status = db.Column(
        db.String(10),
        nullable=False,
        default=DonationStatus.PENDING,
        index=True,
    )
    checkout_request_id = db.Column(db.String(100), nullable=True, unique=True, index=True)
    merchant_request_id = db.Column(db.String(100), nullable=True)
    mpesa_receipt_number = db.Column(db.String(50), nullable=True)
    failure_reason = db.Column(db.String(255), nullable=True)

    # ── Timestamps ──────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=utc_now, index=True)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    donor = db.relationship("User", back_populates="donations")
    charity = db.relationship("Charity", back_populates="donations")
    
    def __init__(self, amount, donor_id, charity_id, **kwargs):
        """
        Initialize a new donation.
        
        Args:
            amount: Donation amount in cents (must be positive)
            donor_id: ID of the donating user
            charity_id: ID of the receiving charity
        """
        if amount <= 0:
            raise ValueError("Donation amount must be positive")
        
        super().__init__(
            amount=amount,
            donor_id=donor_id,
            charity_id=charity_id,
            **kwargs
        )
    
    @property
    def amount_kes(self):
        """
        Get donation amount in KES (major units).
        
        Returns:
            float: Amount in KES
        """
        return self.amount / 100
    
    def to_dict(self, include_donor=False):
        """
        Convert donation to dictionary representation.
        
        Args:
            include_donor: Whether to include donor_id (respects anonymity)
            
        Returns:
            dict: Donation data
        """
        data = {
            "id": self.id,
            "amount": self.amount,
            "amount_kes": self.amount_kes,
            "charity_id": self.charity_id,
            "charity_name": self.charity.name if self.charity else None,
            "is_anonymous": self.is_anonymous,
            "is_recurring": self.is_recurring,
            "message": self.message,
            "status": self.status,
            "phone_number": self.phone_number,
            "checkout_request_id": self.checkout_request_id,
            "mpesa_receipt_number": self.mpesa_receipt_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Only include donor_id if requested AND not anonymous
        if include_donor and not self.is_anonymous:
            data["donor_id"] = self.donor_id
        
        return data
    
    def __repr__(self):
        return f"<Donation id={self.id} amount={self.amount} status={self.status}>"
