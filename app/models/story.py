"""
Story Model.

Handles beneficiary stories posted by charities.
Donors can view these stories to see the impact of their donations.
"""
from datetime import datetime, timezone

from app.extensions import db


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Story(db.Model):
    """
    Beneficiary story posted by a charity.

    Charities create stories to show donors the impact of their contributions.
    Stories can include a title, content, and optional image.
    """
    __tablename__ = "stories"

    id = db.Column(db.Integer, primary_key=True)
    charity_id = db.Column(
        db.Integer,
        db.ForeignKey("charities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(500), nullable=True)
    is_published = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    charity = db.relationship("Charity", back_populates="stories")

    def to_dict(self):
        return {
            "id": self.id,
            "charity_id": self.charity_id,
            "charity_name": self.charity.name if self.charity else None,
            "title": self.title,
            "content": self.content,
            "image_path": self.image_path,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Story id={self.id} title={self.title!r}>"
