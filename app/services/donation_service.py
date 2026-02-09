"""
Donation Service.

Business logic for donation-related operations with M-Pesa payment integration.
"""
from app.extensions import db
from app.models import Donation
from app.services.payment_service import PaymentService


class DonationService:
    """Service class for donation operations."""
    
    @staticmethod
    def initiate_donation(donor_id, charity_id, amount, phone_number, is_anonymous=False, 
                         is_recurring=False, message=None):
        """
        Initiate donation by creating payment intent.
        
        Args:
            donor_id: ID of the donor
            charity_id: ID of the charity
            amount: Donation amount in KES
            phone_number: Donor's M-Pesa phone number
            is_anonymous: Whether to hide donor identity
            is_recurring: Whether this is a recurring donation
            message: Optional message to charity
            
        Returns:
            dict: Payment intent result with checkout_request_id
            
        Raises:
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError("Donation amount must be positive")
        
        # Create payment intent
        account_reference = f"DONATION-{donor_id}-{charity_id}"
        transaction_desc = f"Donation to Charity {charity_id}"
        
        payment_result = PaymentService.create_payment_intent(
            amount=amount,
            phone_number=phone_number,
            account_reference=account_reference,
            transaction_desc=transaction_desc
        )
        
        if not payment_result["success"]:
            raise ValueError(payment_result.get("error", "Payment initiation failed"))
        
        # Store pending donation data for callback processing
        payment_result["pending_donation"] = {
            "donor_id": donor_id,
            "charity_id": charity_id,
            "amount": int(amount * 100),  # Convert to cents
            "is_anonymous": is_anonymous,
            "is_recurring": is_recurring,
            "message": message
        }
        
        return payment_result
    
    @staticmethod
    def create_donation_after_payment(checkout_request_id, donor_id, charity_id, 
                                     amount_cents, transaction_id, is_anonymous=False, 
                                     is_recurring=False, message=None):
        """
        Create donation record after successful payment confirmation.
        
        Args:
            checkout_request_id: M-Pesa checkout request ID
            donor_id: ID of the donor
            charity_id: ID of the charity
            amount_cents: Donation amount in cents
            transaction_id: M-Pesa transaction ID
            is_anonymous: Whether to hide donor identity
            is_recurring: Whether this is a recurring donation
            message: Optional message to charity
            
        Returns:
            Donation: Created donation
        """
        donation = Donation(
            amount=amount_cents,
            donor_id=donor_id,
            charity_id=charity_id,
            is_anonymous=is_anonymous,
            is_recurring=is_recurring,
            message=message
        )
        
        db.session.add(donation)
        db.session.commit()
        
        return donation
    
    @staticmethod
    def process_payment_callback(callback_data, pending_donation_data):
        """
        Process M-Pesa callback and create donation if payment successful.
        
        Args:
            callback_data: Callback data from M-Pesa
            pending_donation_data: Pending donation data stored during initiation
            
        Returns:
            dict: Result with donation object if successful
        """
        payment_result = PaymentService.confirm_payment(callback_data)
        
        if not payment_result["success"]:
            return {
                "success": False,
                "error": payment_result.get("error", "Payment confirmation failed")
            }
        
        # Create donation after successful payment
        donation = DonationService.create_donation_after_payment(
            checkout_request_id=payment_result["checkout_request_id"],
            donor_id=pending_donation_data["donor_id"],
            charity_id=pending_donation_data["charity_id"],
            amount_cents=pending_donation_data["amount"],
            transaction_id=payment_result["transaction_id"],
            is_anonymous=pending_donation_data.get("is_anonymous", False),
            is_recurring=pending_donation_data.get("is_recurring", False),
            message=pending_donation_data.get("message")
        )
        
        return {
            "success": True,
            "donation": donation,
            "transaction_id": payment_result["transaction_id"],
            "transaction_reference": PaymentService.get_transaction_reference(
                payment_result["checkout_request_id"]
            )
        }
    
    @staticmethod
    def get_donation(donation_id):
        """Get donation by ID."""
        return Donation.query.get(donation_id)
    
    @staticmethod
    def get_donations_by_donor(donor_id, limit=None):
        """Get all donations made by a donor."""
        query = Donation.query.filter_by(donor_id=donor_id).order_by(
            Donation.created_at.desc()
        )
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @staticmethod
    def get_donations_by_charity(charity_id, limit=None):
        """Get all donations received by a charity."""
        query = Donation.query.filter_by(charity_id=charity_id).order_by(
            Donation.created_at.desc()
        )
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @staticmethod
    def get_donor_stats(donor_id):
        """Get statistics for a donor."""
        total_donated = db.session.query(
            db.func.coalesce(db.func.sum(Donation.amount), 0)
        ).filter(Donation.donor_id == donor_id).scalar() or 0
        
        donation_count = Donation.query.filter_by(donor_id=donor_id).count()
        
        unique_charities = db.session.query(
            db.func.count(db.func.distinct(Donation.charity_id))
        ).filter(Donation.donor_id == donor_id).scalar() or 0
        
        return {
            "total_donated": total_donated / 100,  # Return dollars for frontend
            "donation_count": donation_count,
            "charities_supported": unique_charities,
            "active_recurring": Donation.query.filter_by(donor_id=donor_id, is_recurring=True).count()
        }
    
    @staticmethod
    def get_total_donations_amount():
        """Get total amount of all donations on the platform."""
        result = db.session.query(
            db.func.coalesce(db.func.sum(Donation.amount), 0)
        ).scalar()
        return result or 0
    
    @staticmethod
    def get_total_donation_count():
        """Get total number of donations on the platform."""
        return Donation.query.count()

    @staticmethod
    def get_recurring_donations(donor_id):
        """Get recurring donations for a donor."""
        return Donation.query.filter_by(donor_id=donor_id, is_recurring=True).all()
