"""
Subscription Model.

Tracks recurring donation commitments.
"""
from datetime import datetime, timezone, timedelta

from app.extensions import db


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class SubscriptionStatus:
    active = "active"
    paused = "paused"
    cancelled = "cancelled"


class Subscription(db.Model):
    """
    Recurring donation subscription.
    """
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
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
    
    # Donation details
    amount = db.Column(db.Integer, nullable=False)  # Amount in cents
    phone_number = db.Column(db.String(15), nullable=False)  # For STK Push
    message = db.Column(db.Text, nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    
    # Scheduling
    frequency = db.Column(db.String(20), default="monthly")  # daily, weekly, monthly
    status = db.Column(db.String(20), default=SubscriptionStatus.active, index=True)
    next_run_at = db.Column(db.DateTime, nullable=False, index=True)
    last_run_at = db.Column(db.DateTime, nullable=True)
    
    # Meta
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    donor = db.relationship("User", backref="subscriptions")
    charity = db.relationship("Charity", backref="subscriptions_received")

    def __init__(self, donor_id, charity_id, amount, phone_number, start_date=None, **kwargs):
        self.donor_id = donor_id
        self.charity_id = charity_id
        self.amount = amount
        self.phone_number = phone_number
        
        # Default next run is 30 days from now if not specified
        if not start_date:
            start_date = utc_now() + timedelta(days=30)
        self.next_run_at = start_date
        
        super().__init__(**kwargs)

    @property
    def amount_kes(self):
        return self.amount / 100

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "amount_kes": self.amount_kes,
            "frequency": self.frequency,
            "status": self.status,
            "next_run_at": self.next_run_at.isoformat(),
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "charity_name": self.charity.name if self.charity else "Unknown",
            "created_at": self.created_at.isoformat(),
        }
