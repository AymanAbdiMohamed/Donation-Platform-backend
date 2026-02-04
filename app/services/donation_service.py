"""
Donation Service.

Business logic for donation-related operations.
"""
from app.extensions import db
from app.models import Donation, Charity, User


class DonationService:
    """Service class for donation operations."""
    
    @staticmethod
    def create_donation(donor_id, charity_id, amount, is_anonymous=False, is_recurring=False, message=""):
        """
        Create a new donation.
        
        Args:
            donor_id: Donating user's ID
            charity_id: Receiving charity's ID
            amount: Donation amount in cents (must be positive)
            is_anonymous: Whether donation is anonymous
            is_recurring: Whether donation is recurring
            message: Optional message to charity
            
        Returns:
            Donation: Created donation
            
        Raises:
            ValueError: If validation fails
        """
        # Validate amount
        if amount <= 0:
            raise ValueError("Donation amount must be positive")
        
        # Validate donor exists
        donor = User.query.get(donor_id)
        if not donor:
            raise ValueError("Donor not found")
        
        # Validate charity exists and is active
        charity = Charity.query.filter_by(id=charity_id, is_active=True).first()
        if not charity:
            raise ValueError("Charity not found or inactive")
        
        donation = Donation(
            amount=amount,
            donor_id=donor_id,
            charity_id=charity_id,
            is_anonymous=is_anonymous,
            is_recurring=is_recurring,
            message=message or None
        )
        
        db.session.add(donation)
        db.session.commit()
        
        return donation
    
    @staticmethod
    def get_donation(donation_id):
        """Get donation by ID."""
        return Donation.query.get(donation_id)
    
    @staticmethod
    def get_donations_by_donor(donor_id, limit=None):
        """
        Get all donations made by a donor.
        
        Args:
            donor_id: Donor's user ID
            limit: Optional limit on number of results
            
        Returns:
            list: List of donations
        """
        query = Donation.query.filter_by(donor_id=donor_id).order_by(
            Donation.created_at.desc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_donations_by_charity(charity_id, limit=None):
        """
        Get all donations received by a charity.
        
        Args:
            charity_id: Charity's ID
            limit: Optional limit on number of results
            
        Returns:
            list: List of donations
        """
        query = Donation.query.filter_by(charity_id=charity_id).order_by(
            Donation.created_at.desc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_total_donations_amount():
        """
        Get total amount of all donations on platform.
        
        Returns:
            int: Total donations in cents
        """
        result = db.session.query(
            db.func.coalesce(db.func.sum(Donation.amount), 0)
        ).scalar()
        return result or 0
    
    @staticmethod
    def get_total_donation_count():
        """
        Get total number of donations on platform.
        
        Returns:
            int: Number of donations
        """
        return Donation.query.count()
    
    @staticmethod
    def get_recent_donations(limit=10):
        """
        Get most recent donations.
        
        Args:
            limit: Number of donations to return
            
        Returns:
            list: List of recent donations
        """
        return Donation.query.order_by(Donation.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_donor_total(donor_id):
        """
        Get total amount donated by a donor.
        
        Args:
            donor_id: Donor's user ID
            
        Returns:
            int: Total donated in cents
        """
        result = db.session.query(
            db.func.coalesce(db.func.sum(Donation.amount), 0)
        ).filter(Donation.donor_id == donor_id).scalar()
        return result or 0
