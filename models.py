"""
SQLAlchemy User model.
"""
from sqlalchemy import Column, Integer, String
from db import Base


class User(Base):
    """User model - donors, charities, and admins."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False)  # DONOR, CHARITY, ADMIN

    def __repr__(self):
        return f"<User id={self.id} username={self.username} role={self.role}>"
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
