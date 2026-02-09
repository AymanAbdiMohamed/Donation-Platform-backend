"""
Charity Service.

Business logic for charity-related operations.
"""
from app.extensions import db
from app.models import Charity, CharityApplication, CharityDocument


class CharityService:
    """Service class for charity operations."""

    # ==================
    # Application Methods
    # ==================

    @staticmethod
    def create_application(user_id, name, description=""):
        """
        Create a new charity application draft.

        Raises:
            ValueError: If user already has active application or charity
        """

        # Prevent multiple active applications
        existing = CharityApplication.query.filter(
            CharityApplication.user_id == user_id,
            CharityApplication.status.in_(["draft", "submitted"])
        ).first()

        if existing:
            raise ValueError(
                f"You already have an application in status: {existing.status}"
            )

        # Prevent duplicate charity
        existing_charity = Charity.query.filter_by(user_id=user_id).first()
        if existing_charity:
            raise ValueError("You already have an approved charity")

        application = CharityApplication(
            user_id=user_id,
            name=name,
            description=description,
            status="draft",
            step=1
        )

        db.session.add(application)
        db.session.commit()

        return application

    @staticmethod
    def save_application_step(user_id, step_data):
        """Save data for current application step."""

        application = CharityService.get_latest_application(user_id)

        if not application:
            raise ValueError("No application found")

        if not application.can_edit():
            raise ValueError(
                f"Cannot edit application with status: {application.status}"
            )

        application.save_step(step_data)
        db.session.commit()

        return application

    @staticmethod
    def advance_application_step(user_id):
        """Advance to next step."""

        application = CharityService.get_latest_application(user_id)

        if not application:
            raise ValueError("No application found")

        if not application.can_edit():
            raise ValueError(
                f"Cannot edit application with status: {application.status}"
            )

        if application.step < application.TOTAL_STEPS:
            application.step += 1
            db.session.commit()
            return application, True

        return application, False

    @staticmethod
    def submit_application(user_id):
        """Submit application for review."""

        application = CharityService.get_latest_application(user_id)

        if not application:
            raise ValueError("No application found")

        if application.status != "draft":
            raise ValueError(
                f"Application is not in draft status (current: {application.status})"
            )

        application.submit()
        db.session.commit()

        return application

    @staticmethod
    def get_application(application_id):
        return CharityApplication.query.get(application_id)

    @staticmethod
    def get_user_applications(user_id):
        return CharityApplication.query.filter_by(user_id=user_id).order_by(
            CharityApplication.created_at.desc()
        ).all()

    @staticmethod
    def get_latest_application(user_id):
        return CharityApplication.query.filter_by(user_id=user_id).order_by(
            CharityApplication.created_at.desc()
        ).first()

    @staticmethod
    def get_applications_by_status(status=None):
        """
        Get applications, optionally filtered by status.

        Args:
            status: One of CharityApplication.VALID_STATUSES or None for all.
        """
        query = CharityApplication.query
        if status:
            query = query.filter_by(status=status)
        return query.order_by(CharityApplication.created_at.desc()).all()

    @staticmethod
    def approve_application(application_id):
        """
        Approve application and create charity.
        """

        application = CharityApplication.query.get(application_id)

        if not application:
            raise ValueError("Application not found")

        if not application.is_submitted():
            raise ValueError(
                f"Application is not submitted (current: {application.status})"
            )

        # Mark approved
        application.approve()

        # Create charity from application data
        charity = Charity(
            name=application.name,
            description=application.description,
            mission=application.mission,
            goals=application.goals,
            category=application.category,
            location=application.location,
            contact_email=application.contact_email,
            contact_phone=application.contact_phone,
            website=application.website,
            address=application.address,
            user_id=application.user_id
        )

        db.session.add(charity)
        db.session.commit()

        return application, charity

    @staticmethod
    def reject_application(application_id, reason=""):
        application = CharityApplication.query.get(application_id)

        if not application:
            raise ValueError("Application not found")

        if not application.is_submitted():
            raise ValueError(
                f"Application is not submitted (current: {application.status})"
            )

        application.reject(reason)
        db.session.commit()

        return application

    # ==================
    # Document Methods
    # ==================

    @staticmethod
    def add_document(application_id, document_type, file_path,
                     original_filename, file_size=None, mime_type=None):

        application = CharityApplication.query.get(application_id)

        if not application:
            raise ValueError("Application not found")

        if document_type not in CharityDocument.VALID_TYPES:
            raise ValueError(f"Invalid document type: {document_type}")

        document = CharityDocument(
            application_id=application_id,
            document_type=document_type,
            file_path=file_path,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type
        )

        db.session.add(document)
        db.session.commit()

        return document

    @staticmethod
    def get_application_documents(application_id):
        return CharityDocument.query.filter_by(
            application_id=application_id
        ).order_by(CharityDocument.created_at.desc()).all()

    @staticmethod
    def delete_document(document_id):
        document = CharityDocument.query.get(document_id)

        if not document:
            raise ValueError("Document not found")

        db.session.delete(document)
        db.session.commit()

        return True

    # ==================
    # Charity Methods
    # ==================

    @staticmethod
    def get_charity(charity_id):
        return Charity.query.get(charity_id)

    @staticmethod
    def get_charity_by_user(user_id):
        return Charity.query.filter_by(user_id=user_id).first()

    @staticmethod
    def get_active_charities():
        return Charity.query.filter_by(is_active=True).all()

    @staticmethod
    def get_all_charities():
        return Charity.query.all()

    @staticmethod
    def update_charity(charity_id, **kwargs):

        charity = Charity.query.get(charity_id)
        if not charity:
            return None

        allowed_fields = (
            "name", "description", "logo_path", "category", "location",
            "contact_email", "contact_phone", "website",
            "address", "mission", "goals"
        )

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(charity, key, value)

        db.session.commit()
        return charity

    @staticmethod
    def deactivate_charity(charity_id):

        charity = Charity.query.get(charity_id)
        if not charity:
            return None

        charity.deactivate()
        db.session.commit()
        return charity

    @staticmethod
    def activate_charity(charity_id):

        charity = Charity.query.get(charity_id)
        if not charity:
            return None

        charity.activate()
        db.session.commit()
        return charity

    @staticmethod
    def get_charity_stats(charity_id):

        charity = Charity.query.get(charity_id)
        if not charity:
            return None

        return {
            "total_donations": charity.get_total_donations(),
            "donation_count": charity.get_donation_count(),
        }
