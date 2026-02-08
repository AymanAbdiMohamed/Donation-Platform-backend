"""
CharityDocument Model.

Handles document uploads for charity verification (tax documents, certificates, etc.).
"""
from datetime import datetime, timezone

from app.extensions import db


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class CharityDocument(db.Model):
    """
    Document uploaded for charity verification.
    
    Documents can include:
    - Tax registration certificates
    - Proof of address
    - Legal incorporation documents
    - Other verification materials
    """
    __tablename__ = "charity_documents"
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("charity_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    document_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes
    mime_type = db.Column(db.String(100), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.Integer, nullable=True)  # Admin user ID
    created_at = db.Column(db.DateTime, default=utc_now)
    
    # Relationships
    application = db.relationship(
        "CharityApplication",
        back_populates="documents"
    )
    
    # Valid document types
    VALID_TYPES = (
        "tax_certificate",
        "proof_of_address",
        "legal_incorporation",
        "annual_report",
        "financial_statement",
        "other"
    )
    
    def verify(self, admin_user_id):
        """
        Mark document as verified.
        
        Args:
            admin_user_id: ID of admin who verified the document
        """
        self.is_verified = True
        self.verified_at = utc_now()
        self.verified_by = admin_user_id
    
    def to_dict(self):
        """Convert document to dictionary representation."""
        return {
            "id": self.id,
            "application_id": self.application_id,
            "document_type": self.document_type,
            "file_path": self.file_path,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "is_verified": self.is_verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_by": self.verified_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<CharityDocument id={self.id} type={self.document_type}>"

