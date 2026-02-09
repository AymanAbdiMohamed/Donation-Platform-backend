"""
Email Utility.

Handles email sending functionality.

TODO: EmailService credentials (SMTP_USER, SMTP_PASSWORD, FROM_EMAIL) are not
configured. Emails currently run in mock mode (printed to console). To enable
real delivery, call EmailService.configure() at app startup or load from env vars.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailService:
    """Service class for email operations."""
    
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = None
    SMTP_PASSWORD = None
    FROM_EMAIL = None
    
    @staticmethod
    def configure(smtp_host=None, smtp_port=None, smtp_user=None, 
                 smtp_password=None, from_email=None):
        """Configure email service settings."""
        if smtp_host:
            EmailService.SMTP_HOST = smtp_host
        if smtp_port:
            EmailService.SMTP_PORT = smtp_port
        if smtp_user:
            EmailService.SMTP_USER = smtp_user
        if smtp_password:
            EmailService.SMTP_PASSWORD = smtp_password
        if from_email:
            EmailService.FROM_EMAIL = from_email


def send_email(to_email, subject, body, html_body=None, from_email=None):
    """
    Send an email.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: HTML email body (optional)
        from_email: Sender email address (optional)
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        sender = from_email or EmailService.FROM_EMAIL
        
        if not sender:
            print("Warning: FROM_EMAIL not configured. Email not sent.")
            return False
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        
        text_part = MIMEText(body, "plain")
        msg.attach(text_part)
        
        if html_body:
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)
        
        if not EmailService.SMTP_USER or not EmailService.SMTP_PASSWORD:
            print(f"Mock email sent to {to_email}: {subject}")
            return True
        
        with smtplib.SMTP(EmailService.SMTP_HOST, EmailService.SMTP_PORT) as server:
            server.starttls()
            server.login(EmailService.SMTP_USER, EmailService.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


# TODO: send_donation_receipt is unused — ReceiptService.send_receipt_email()
# handles receipt formatting and delivery. Remove this function once confirmed
# that no future consumer needs it, or refactor ReceiptService to call it.
def send_donation_receipt(donor_email, receipt):
    """
    Send donation receipt email.
    
    Args:
        donor_email: Donor's email address
        receipt: Receipt dictionary from ReceiptService
        
    Returns:
        bool: True if email sent successfully
    """
    subject = f"Donation Receipt - {receipt['receipt_number']}"
    
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
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Donation Receipt</h2>
                
                <p><strong>Receipt Number:</strong> {receipt['receipt_number']}</p>
                <p><strong>Date:</strong> {receipt['date']}</p>
                
                <h3 style="color: #34495e; margin-top: 20px;">Donation Summary</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background-color: #ecf0f1;">
                        <td style="padding: 10px; border: 1px solid #bdc3c7;"><strong>Amount</strong></td>
                        <td style="padding: 10px; border: 1px solid #bdc3c7;">KES {receipt['amount_dollars']:.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #bdc3c7;"><strong>Charity</strong></td>
                        <td style="padding: 10px; border: 1px solid #bdc3c7;">{receipt['charity']['name']}</td>
                    </tr>
                    <tr style="background-color: #ecf0f1;">
                        <td style="padding: 10px; border: 1px solid #bdc3c7;"><strong>Donor</strong></td>
                        <td style="padding: 10px; border: 1px solid #bdc3c7;">{donor_name}</td>
                    </tr>
                </table>
                
                <h3 style="color: #34495e; margin-top: 20px;">Donation Details</h3>
                <p><strong>Receipt ID:</strong> {receipt['donation_id']}</p>
                <p><strong>Anonymous:</strong> {'Yes' if receipt['is_anonymous'] else 'No'}</p>
                <p><strong>Recurring:</strong> {'Yes' if receipt['is_recurring'] else 'No'}</p>
                
                {f"<p><strong>Message:</strong> {receipt['message']}</p>" if receipt['message'] else ''}
                
                <h3 style="color: #34495e; margin-top: 20px;">Charity Information</h3>
                <p><strong>Name:</strong> {receipt['charity']['name']}</p>
                <p><strong>Email:</strong> {receipt['charity']['contact_email']}</p>
                <p><strong>Address:</strong> {receipt['charity']['address']}</p>
                
                <div style="background-color: #d5f4e6; padding: 15px; margin-top: 20px; border-radius: 5px;">
                    <p style="margin: 0;">Thank you for your generous donation to <strong>{receipt['charity']['name']}</strong>!</p>
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: #555;">This receipt serves as confirmation of your donation for tax purposes.</p>
                </div>
                
                <p style="margin-top: 20px; font-size: 12px; color: #7f8c8d;">Generated: {receipt['generated_at']}</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(donor_email, subject, body, html_body)
