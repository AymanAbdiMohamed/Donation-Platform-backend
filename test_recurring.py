from app import create_app
from app.extensions import db
from app.models import Subscription, User, Charity
from app.services.scheduler_service import SchedulerService
from datetime import datetime, timedelta, timezone

app = create_app()

def test_recurring():
    with app.app_context():
        print("Creating test data...")
        # Create dummy user and charity if not exist (or use existing)
        # For simplicity, let's assume at least one user and charity exists
        # Or fetch first ones
        donor = User.query.filter_by(role="donor").first()
        charity = Charity.query.first()
        
        if not donor or not charity:
            print("Skipping test: No donor or charity found in DB.")
            return

        print(f"Using Donor: {donor.email}, Charity: {charity.name}")

        # Create a subscription due NOW
        sub = Subscription(
            donor_id=donor.id,
            charity_id=charity.id,
            amount=1000, # 10 KES
            phone_number="254712345678",
            frequency="monthly"
        )
        # Force next_run_at to be in the past
        sub.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        db.session.add(sub)
        db.session.commit()
        print(f"Created Subscription #{sub.id} due at {sub.next_run_at}")

        # Run the scheduler job manually
        print("Running scheduler job...")
        SchedulerService.process_recurring_donations()
        
        # Reload subscription
        db.session.refresh(sub)
        print(f"After run: Subscription #{sub.id} next_run_at is {sub.next_run_at}")
        
        if sub.next_run_at > datetime.now(timezone.utc):
            print("SUCCESS: Subscription was processed and rescheduled!")
        else:
            print("FAILURE: Subscription was NOT rescheduled.")

if __name__ == "__main__":
    test_recurring()
