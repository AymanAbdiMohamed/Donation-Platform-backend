"""
Beneficiary Model.

Tracks beneficiaries served by a charity, along with inventory items
distributed to them.
"""
from datetime import datetime, timezone

from app.extensions import db


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Beneficiary(db.Model):
    """
    A beneficiary served by a charity.

    Charities maintain a list of beneficiaries and track what items
    (sanitary towels, soap, etc.) have been sent to each one.
    """
    __tablename__ = "beneficiaries"

    id = db.Column(db.Integer, primary_key=True)
    charity_id = db.Column(
        db.Integer,
        db.ForeignKey("charities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    school = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    charity = db.relationship("Charity", back_populates="beneficiaries")
    inventory_items = db.relationship(
        "InventoryItem",
        back_populates="beneficiary",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_inventory=False):
        data = {
            "id": self.id,
            "charity_id": self.charity_id,
            "name": self.name,
            "age": self.age,
            "location": self.location,
            "school": self.school,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_inventory:
            data["inventory"] = [item.to_dict() for item in self.inventory_items]
        return data

    def __repr__(self):
        return f"<Beneficiary id={self.id} name={self.name!r}>"


class InventoryItem(db.Model):
    """
    An item distributed to a beneficiary.

    Tracks what was sent, how many, and when.
    """
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    beneficiary_id = db.Column(
        db.Integer,
        db.ForeignKey("beneficiaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    date_distributed = db.Column(db.DateTime, default=utc_now)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    beneficiary = db.relationship("Beneficiary", back_populates="inventory_items")

    def to_dict(self):
        return {
            "id": self.id,
            "beneficiary_id": self.beneficiary_id,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "date_distributed": self.date_distributed.isoformat() if self.date_distributed else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<InventoryItem id={self.id} item={self.item_name!r} qty={self.quantity}>"
