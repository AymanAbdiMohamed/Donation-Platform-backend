import sys
from app import create_app
from app.utils.email import send_email

app = create_app()

def test_email_sending():
    """Test sending an email using the configured settings."""
    with app.app_context():
        print("Checking email configuration...")
        server = app.config.get("MAIL_SERVER")
        username = app.config.get("MAIL_USERNAME")
        
        if not username or username == "paste_your_username_here":
            print("ERROR: MAIL_USERNAME not set in .env")
            print("Please edit .env and add your Mailtrap credentials.")
            return

        print(f"Server: {server}")
        print(f"Username: {username}")
        
        recipient = "test@example.com"
        subject = "Mailtrap Test Email"
        body = "This is a test email from your Flask application using Mailtrap."
        
        print(f"\nSending test email to {recipient}...")
        success = send_email(recipient, subject, body)
        
        if success:
            print("SUCCESS: Email sent! Check your Mailtrap inbox.")
        else:
            print("FAILURE: Email could not be sent. Check your logs/credentials.")

if __name__ == "__main__":
    test_email_sending()
