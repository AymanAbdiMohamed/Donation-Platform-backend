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
            "amount_kes": donation.amount_kes,
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
Amount: KES {receipt['amount_kes']:.2f}
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

    @staticmethod
    def generate_pdf_receipt(donation_id):
        """
        Generate a PDF receipt.
        
        Args:
            donation_id: ID of the donation
            
        Returns:
            bytes: PDF content
        """
        from xhtml2pdf import pisa
        from io import BytesIO
        
        receipt = ReceiptService.generate_receipt(donation_id)
        
        # Simple HTML template for the receipt
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Helvetica, Arial, sans-serif; padding: 40px; color: #333; }}
                .header {{ text-align: center; margin-bottom: 40px; border-bottom: 2px solid #ec4899; padding-bottom: 20px; }}
                .title {{ font-size: 24px; font-weight: bold; color: #ec4899; }}
                .meta {{ font-size: 14px; color: #666; margin-top: 10px; }}
                .content {{ margin-bottom: 40px; }}
                .row {{ margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                .label {{ font-weight: bold; width: 150px; display: inline-block; }}
                .value {{ display: inline-block; }}
                .footer {{ text-align: center; font-size: 12px; color: #999; margin-top: 50px; border-top: 1px solid #eee; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">OFFICIAL DONATION RECEIPT</div>
                <div class="meta">Receipt #{receipt['receipt_number']} • {receipt['date'][:10]}</div>
            </div>
            
            <div class="content">
                <div class="row">
                    <span class="label">Amount:</span>
                    <span class="value">KES {receipt['amount_kes']:,.2f}</span>
                </div>
                <div class="row">
                    <span class="label">Charity:</span>
                    <span class="value">{receipt['charity']['name']}</span>
                </div>
                <div class="row">
                    <span class="label">Donor:</span>
                    <span class="value">{receipt['donor']['name'] if not receipt['is_anonymous'] else 'Anonymous'}</span>
                </div>
                <div class="row">
                    <span class="label">Transaction ID:</span>
                    <span class="value">{receipt['donation_id']}</span>
                </div>
                
                <h3 style="margin-top: 30px; color: #333;">Charity Details</h3>
                <div class="row">
                    <span class="label">Address:</span>
                    <span class="value">{receipt['charity']['address']}</span>
                </div>
                <div class="row">
                    <span class="label">Email:</span>
                    <span class="value">{receipt['charity']['contact_email']}</span>
                </div>
            </div>
            
            <div class="footer">
                <p>Thank you for your generous support!</p>
                <p>SheNeeds Platform • Generated on {receipt['generated_at']}</p>
            </div>
        </body>
        </html>
        """
        
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        
        if pisa_status.err:
            raise ValueError("PDF generation failed")
            
        return pdf_buffer.getvalue()
