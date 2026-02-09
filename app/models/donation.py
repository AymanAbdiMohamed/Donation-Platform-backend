"""
Donation Model.

Handles donation records between donors and charities.
"""
from datetime import datetime, timezone

from app.extensions import db


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Donation(db.Model):
    """
    Donation record.
    
    Amount is stored in cents to avoid floating-point issues.
    Example: $50.00 = 5000 cents
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
    created_at = db.Column(db.DateTime, default=utc_now, index=True)
    
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
    def amount_dollars(self):
        """
        Get donation amount in dollars.
        
        Returns:
            float: Amount in dollars
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
            "amount_dollars": self.amount_dollars,
            "charity_id": self.charity_id,
            "charity_name": self.charity.name if self.charity else "Unknown",
            "is_anonymous": self.is_anonymous,
            "is_recurring": self.is_recurring,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        # Only include donor_id if requested AND not anonymous
        if include_donor and not self.is_anonymous:
            data["donor_id"] = self.donor_id
        
        return data
    
    def __repr__(self):
        return f"<Donation id={self.id} amount={self.amount} charity_id={self.charity_id}>"
