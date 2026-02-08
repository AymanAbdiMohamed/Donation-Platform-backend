"""
Charity Service.

Business logic for charity-related operations.
"""
from app.extensions import db
from app.models import Charity, CharityApplication


class CharityService:
    """Service class for charity operations."""
    
    # ==================
    # Application Methods
    # ==================
    
    @staticmethod
    def create_application(user_id, name, description="", contact_email=None, contact_phone=None, 
                          registration_number=None, country=None):
        """
        Create a new charity application.
        
        Args:
            user_id: Applicant's user ID
            name: Charity name
            description: Charity description
            contact_email: Contact email
            contact_phone: Contact phone
            registration_number: Registration number
            country: Country of operation
            
        Returns:
            CharityApplication: Created application
            
        Raises:
            ValueError: If user has pending application or already has charity
        """
        # Check for existing pending application
        existing_pending = CharityApplication.query.filter_by(
            user_id=user_id,
            status="pending"
        ).first()
        
        if existing_pending:
            raise ValueError("You already have a pending application")
        
        # Check if user already has a charity
        existing_charity = Charity.query.filter_by(user_id=user_id).first()
        if existing_charity:
            raise ValueError("You already have an approved charity")
        
        application = CharityApplication(
            user_id=user_id,
            name=name,
            description=description,
            contact_email=contact_email,
            contact_phone=contact_phone,
            registration_number=registration_number,
            country=country
        )
        
        db.session.add(application)
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
            status: Filter by status (pending, approved, rejected) or None for all
            
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
            ValueError: If application not found or not pending
        """
        application = CharityApplication.query.get(application_id)
        
        if not application:
            raise ValueError("Application not found")
        
        if not application.is_pending():
            raise ValueError(f"Application is already {application.status}")
        
        # Approve the application
        application.approve()
        
        # Create the charity
        charity = Charity(
            name=application.name,
            description=application.description,
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
            ValueError: If application not found or not pending
        """
        application = CharityApplication.query.get(application_id)
        
        if not application:
            raise ValueError("Application not found")
        
        if not application.is_pending():
            raise ValueError(f"Application is already {application.status}")
        
        application.reject(reason)
        db.session.commit()
        
        return application
    
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
            **kwargs: Fields to update (name, description)
            
        Returns:
            Charity: Updated charity or None
        """
        charity = Charity.query.get(charity_id)
        if not charity:
            return None
        
        allowed_fields = ('name', 'description')
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
