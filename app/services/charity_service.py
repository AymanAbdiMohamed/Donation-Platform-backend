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
        Create a new charity application.
        
        Args:
            user_id: Applicant's user ID
            name: Charity name
            description: Charity description
            
        Returns:
            CharityApplication: Created application
            
        Raises:
            ValueError: If user has pending/submitted application or already has charity
        """
        # Check for existing draft or submitted application
        existing = CharityApplication.query.filter(
            CharityApplication.user_id == user_id,
            CharityApplication.status.in_(["draft", "submitted"])
        ).first()
        
        if existing:
            raise ValueError(f"You already have an application in status: {existing.status}")
        
        # Check if user already has a charity
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
        """
        Save data for the current step of an application.
        
        Args:
            user_id: User ID
            step_data: Dictionary of fields to save
            
        Returns:
            CharityApplication: Updated application
            
        Raises:
            ValueError: If no application found or cannot edit
        """
        application = CharityService.get_latest_application(user_id)
        
        if not application:
            raise ValueError("No application found")
        
        if not application.can_edit():
            raise ValueError(f"Cannot edit application with status: {application.status}")
        
        # Save step data
        application.save_step(step_data)
        db.session.commit()
        
        return application
    
    @staticmethod
    def advance_application_step(user_id):
        """
        Advance application to next step.
        
        Args:
            user_id: User ID
            
        Returns:
            tuple: (CharityApplication, bool) - application and whether step advanced
            
        Raises:
            ValueError: If no application found or cannot advance
        """
        application = CharityService.get_latest_application(user_id)
        
        if not application:
            raise ValueError("No application found")
        
        if not application.can_edit():
            raise ValueError(f"Cannot edit application with status: {application.status}")
        
        if application.step < application.TOTAL_STEPS:
            application.step += 1
            db.session.commit()
            return application, True
        
        return application, False
    
    @staticmethod
    def submit_application(user_id):
        """
        Submit a draft application for review.
        
        Args:
            user_id: User ID
            
        Returns:
            CharityApplication: Submitted application
            
        Raises:
            ValueError: If no application found or not in draft status
        """
        application = CharityService.get_latest_application(user_id)
        
        if not application:
            raise ValueError("No application found")
        
        if application.status != "draft":
            raise ValueError(f"Application is not in draft status (current: {application.status})")
        
        application.submit()
        db.session.commit()
        
        return application
    
    @staticmethod
    def get_application(application_id):
        """Get application by ID."""
        return CharityApplication.query.get(application_id)
    
    @staticmethod
    def get_user_applications(user_id):
        """Get all applications for a user."""
        return CharityApplication.query.filter_by(user_id=user_id).order_by(
            CharityApplication.created_at.desc()
        ).all()
    
    @staticmethod
    def get_latest_application(user_id):
        """Get user's most recent application."""
        return CharityApplication.query.filter_by(user_id=user_id).order_by(
            CharityApplication.created_at.desc()
        ).first()
    
    @staticmethod
    def get_applications_by_status(status=None):
        """
        Get applications filtered by status.
        
        Args:
            status: Filter by status (draft, submitted, approved, rejected) or None for all
            
        Returns:
            list: List of applications
        """
        query = CharityApplication.query
        if status:
            query = query.filter_by(status=status)
        return query.order_by(CharityApplication.created_at.desc()).all()
    
    @staticmethod
    def approve_application(application_id):
        """
        Approve a charity application and create the charity.
        
        Args:
            application_id: Application ID to approve
            
        Returns:
            tuple: (CharityApplication, Charity) if successful
            
        Raises:
            ValueError: If application not found or not in submitted status
        """
        application = CharityApplication.query.get(application_id)
        
        if not application:
            raise ValueError("Application not found")
        
        if not application.is_submitted():
            raise ValueError(f"Application is not submitted (current: {application.status})")
        
        # Approve the application
        application.approve()
        
        # Create the charity with all details from application
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
        """
        Reject a charity application.
        
        Args:
            application_id: Application ID to reject
            reason: Rejection reason
            
        Returns:
            CharityApplication: Rejected application
            
        Raises:
            ValueError: If application not found or not in submitted status
        """
        application = CharityApplication.query.get(application_id)
        
        if not application:
            raise ValueError("Application not found")
        
        if not application.is_submitted():
            raise ValueError(f"Application is not submitted (current: {application.status})")
        
        application.reject(reason)
        db.session.commit()
        
        return application
    
    # ==================
    # Document Methods
    # ==================
    
    @staticmethod
    def add_document(application_id, document_type, file_path, original_filename, 
                     file_size=None, mime_type=None):
        """
        Add a document to an application.
        
        Args:
            application_id: Application ID
            document_type: Type of document
            file_path: Path to saved file
            original_filename: Original filename
            file_size: File size in bytes
            mime_type: MIME type of file
            
        Returns:
            CharityDocument: Created document
            
        Raises:
            ValueError: If application not found or invalid document type
        """
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
        """
        Get all documents for an application.
        
        Args:
            application_id: Application ID
            
        Returns:
            list: List of documents
        """
        return CharityDocument.query.filter_by(
            application_id=application_id
        ).order_by(CharityDocument.created_at.desc()).all()
    
    @staticmethod
    def delete_document(document_id):
        """
        Delete a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            bool: True if deleted successfully
            
        Raises:
            ValueError: If document not found
        """
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
        """Get charity by ID."""
        return Charity.query.get(charity_id)
    
    @staticmethod
    def get_charity_by_user(user_id):
        """Get charity by user ID."""
        return Charity.query.filter_by(user_id=user_id).first()
    
    @staticmethod
    def get_active_charities():
        """Get all active charities."""
        return Charity.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_all_charities():
        """Get all charities (including inactive)."""
        return Charity.query.all()
    
    @staticmethod
    def update_charity(charity_id, **kwargs):
        """
        Update charity details.
        
        Args:
            charity_id: Charity ID
            **kwargs: Fields to update (name, description, logo_path, category, 
                      location, contact_email, contact_phone, website, address, 
                      mission, goals)
            
        Returns:
            Charity: Updated charity or None
        """
        charity = Charity.query.get(charity_id)
        if not charity:
            return None
        
        allowed_fields = (
            'name', 
            'description', 
            'logo_path', 
            'category', 
            'location', 
            'contact_email', 
            'contact_phone', 
            'website', 
            'address',
            'mission',
            'goals'
        )
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(charity, key, value)
        
        db.session.commit()
        return charity
    
    @staticmethod
    def deactivate_charity(charity_id):
        """
        Deactivate a charity.
        
        Args:
            charity_id: Charity ID
            
        Returns:
            Charity: Deactivated charity or None
        """
        charity = Charity.query.get(charity_id)
        if not charity:
            return None
        
        charity.deactivate()
        db.session.commit()
        return charity
    
    @staticmethod
    def activate_charity(charity_id):
        """
        Reactivate a charity.
        
        Args:
            charity_id: Charity ID
            
        Returns:
            Charity: Activated charity or None
        """
        charity = Charity.query.get(charity_id)
        if not charity:
            return None
        
        charity.activate()
        db.session.commit()
        return charity
    
    @staticmethod
    def get_charity_stats(charity_id):
        """
        Get statistics for a charity.
        
        Args:
            charity_id: Charity ID
            
        Returns:
            dict: Charity statistics
        """
        charity = Charity.query.get(charity_id)
        if not charity:
            return None
        
        return {
            "total_donations": charity.get_total_donations(),
            "donation_count": charity.get_donation_count(),
        }
