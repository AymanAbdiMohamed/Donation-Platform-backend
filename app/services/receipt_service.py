"""
Receipt Service.

Handles generation of donation receipts and email formatting.
"""
from datetime import datetime, timezone


def utc_now():
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ReceiptService:
    """Service class for receipt generation operations."""
    
    @staticmethod
    def generate_receipt(donation_id):
        """
        Generate a receipt for a donation.
        
        Args:
            donation_id: ID of the donation
            
        Returns:
            dict: Receipt details with donation summary
            
        Raises:
            ValueError: If donation not found
        """
        from app.models import Donation, User, Charity
        
        donation = Donation.query.get(donation_id)
        
        if not donation:
            raise ValueError("Donation not found")
        
        donor = User.query.get(donation.donor_id)
        charity = Charity.query.get(donation.charity_id)
        
        if not donor or not charity:
            raise ValueError("Donor or charity not found")
        
        receipt_number = ReceiptService._generate_receipt_number(donation_id)
        
        receipt = {
            "receipt_number": receipt_number,
            "donation_id": donation.id,
            "date": donation.created_at.isoformat() if donation.created_at else None,
            "amount": donation.amount,
            "amount_dollars": donation.amount_dollars,
            "donor": {
                "name": donor.username,
                "email": donor.email if not donation.is_anonymous else None
            },
            "charity": {
                "name": charity.name,
                "contact_email": charity.contact_email,
                "address": charity.address
            },
            "is_anonymous": donation.is_anonymous,
            "is_recurring": donation.is_recurring,
            "message": donation.message,
            "generated_at": utc_now().isoformat()
        }
        
        return receipt
    
    @staticmethod
    def _generate_receipt_number(donation_id):
        """Generate unique receipt number."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"RCP-{timestamp}-{donation_id:06d}"
    
    @staticmethod
    def format_receipt_email(receipt):
        """
        Format receipt as email body.
        
        Args:
            receipt: Receipt dictionary
            
        Returns:
            str: Formatted email body
        """
        donor_name = receipt["donor"]["name"] if not receipt["is_anonymous"] else "Anonymous Donor"
        
        body = f"""
DONATION RECEIPT

Receipt Number: {receipt['receipt_number']}
Date: {receipt['date']}

DONATION SUMMARY
================
Amount: KES {receipt['amount_dollars']:.2f}
Charity: {receipt['charity']['name']}
Donor: {donor_name}

DONATION DETAILS
================
Receipt ID: {receipt['donation_id']}
Anonymous: {'Yes' if receipt['is_anonymous'] else 'No'}
Recurring: {'Yes' if receipt['is_recurring'] else 'No'}

{f"Message: {receipt['message']}" if receipt['message'] else ''}

CHARITY INFORMATION
===================
Name: {receipt['charity']['name']}
Email: {receipt['charity']['contact_email']}
Address: {receipt['charity']['address']}

Thank you for your generous donation to {receipt['charity']['name']}!

This receipt serves as confirmation of your donation for tax purposes.
Generated: {receipt['generated_at']}
        """.strip()
        
        return body
    
    @staticmethod
    def send_receipt_email(donation_id):
        """
        Send receipt via email to donor.
        
        Args:
            donation_id: ID of the donation
            
        Returns:
            bool: True if email sent successfully
        """
        from app.models import Donation, User
        from app.utils.email import send_email
        
        donation = Donation.query.get(donation_id)
        
        if not donation:
            raise ValueError("Donation not found")
        
        donor = User.query.get(donation.donor_id)
        
        if not donor:
            raise ValueError("Donor not found")
        
        receipt = ReceiptService.generate_receipt(donation_id)
        subject = f"Donation Receipt - {receipt['receipt_number']}"
        body = ReceiptService.format_receipt_email(receipt)
        
        return send_email(
            to_email=donor.email,
            subject=subject,
            body=body
        )
