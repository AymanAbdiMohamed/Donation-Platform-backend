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

    Status workflow: draft -> submitted -> approved/rejected

    Multi-step application process:
    - Step 1: Basic Info
    - Step 2: Mission & Goals
    - Step 3: Contact & Location
    - Step 4: Documents & Review
    """
    __tablename__ = "charity_applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Basic info
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)

    # Mission
    mission = db.Column(db.Text, nullable=True)
    goals = db.Column(db.Text, nullable=True)

    # Registration / verification
    registration_number = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)

    # Contact & location
    location = db.Column(db.String(200), nullable=True)
    address = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(200), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(200), nullable=True)

    # Workflow
    status = db.Column(db.String(20), default="draft", index=True)
    step = db.Column(db.Integer, default=1)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    submitted_at = db.Column(db.DateTime, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    applicant = db.relationship("User", back_populates="applications")
    documents = db.relationship(
        "CharityDocument",
        back_populates="application",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    VALID_STATUSES = ("draft", "submitted", "approved", "rejected")
    """Canonical application status values. 'submitted' is displayed as
    'pending' in the admin UI (see admin routes for the mapping)."""
    TOTAL_STEPS = 4

    def approve(self):
        self.status = "approved"
        self.reviewed_at = utc_now()

    def reject(self, reason=""):
        self.status = "rejected"
        self.rejection_reason = reason
        self.reviewed_at = utc_now()

    def submit(self):
        if self.status != "draft":
            raise ValueError(f"Cannot submit application with status: {self.status}")
        self.status = "submitted"
        self.submitted_at = utc_now()

    def save_step(self, step_data: dict):
        allowed_fields = {
            "name", "description", "category",
            "mission", "goals",
            "registration_number", "country",
            "location", "address",
            "contact_email", "contact_phone", "website",
        }
        for field, value in step_data.items():
            if field in allowed_fields:
                setattr(self, field, value)

    def is_draft(self):
        return self.status == "draft"

    def is_submitted(self):
        return self.status == "submitted"

    def is_pending(self):
        """Alias for is_submitted(). The admin UI calls this status 'pending'."""
        return self.status == "submitted"

    def can_edit(self):
        return self.status in ("draft", "submitted")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "mission": self.mission,
            "goals": self.goals,
            "registration_number": self.registration_number,
            "country": self.country,
            "location": self.location,
            "address": self.address,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "website": self.website,
            "status": self.status,
            "step": self.step,
            "total_steps": self.TOTAL_STEPS,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }

    def __repr__(self):
        return f"<CharityApplication id={self.id} name={self.name} status={self.status}>"


class Charity(db.Model):
    """
    Approved charity organization.
    Created when a CharityApplication is approved.
    """
    __tablename__ = "charities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    logo_path = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    address = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(200), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    mission = db.Column(db.Text, nullable=True)
    goals = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="charity")
    donations = db.relationship(
        "Donation",
        back_populates="charity",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    stories = db.relationship(
        "Story",
        back_populates="charity",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    beneficiaries = db.relationship(
        "Beneficiary",
        back_populates="charity",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    VALID_CATEGORIES = (
        "education", "health", "environment", "animals",
        "arts_culture", "community", "humanitarian",
        "research", "religion", "other"
    )

    def activate(self):
        self.is_active = True

    def deactivate(self):
        self.is_active = False

    def get_total_donations(self):
        from app.models.donation import Donation
        return (
            db.session.query(db.func.coalesce(db.func.sum(Donation.amount), 0))
            .filter(Donation.charity_id == self.id)
            .scalar()
        )

    def get_donation_count(self):
        return self.donations.count()

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "logo_path": self.logo_path,
            "category": self.category,
            "location": self.location,
            "address": self.address,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "website": self.website,
            "mission": self.mission,
            "goals": self.goals,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Frontend compatibility aliases
            "region": self.location,  # Frontend uses 'region' for filtering
            "image": self.logo_path,  # Frontend uses 'image' for display
            "verified": True,  # All approved charities are considered verified (MVP)
        }

    def __repr__(self):
        return f"<Charity id={self.id} name={self.name}>"
