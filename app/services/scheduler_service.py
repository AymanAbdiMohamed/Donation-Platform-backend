"""
Scheduler Service.

Handles background tasks for recurring donations.
"""
from datetime import datetime, timedelta, timezone
from app.extensions import db, scheduler
from app.models import Subscription, SubscriptionStatus, Donation
from app.services import PaymentService, DonationService
import logging

logger = logging.getLogger(__name__)

def utc_now():
    return datetime.now(timezone.utc)

class SchedulerService:
    @staticmethod
    def process_recurring_donations():
        """
        Scheduled task to process due recurring donations.
        Triggered daily/hourly by APScheduler.
        """
        logger.info("Starting recurring donation processing...")
        
        with scheduler.app.app_context():
            now = utc_now()
            
            # Find active subscriptions due for payment
            due_subscriptions = Subscription.query.filter(
                Subscription.status == SubscriptionStatus.active,
                Subscription.next_run_at <= now
            ).all()
            
            logger.info(f"Found {len(due_subscriptions)} due subscriptions.")
            
            for sub in due_subscriptions:
                try:
                    SchedulerService._process_single_subscription(sub)
                except Exception as e:
                    logger.error(f"Failed to process subscription {sub.id}: {e}")
            
            db.session.commit()
            logger.info("Recurring donation processing complete.")

    @staticmethod
    def _process_single_subscription(sub):
        """Process a single subscription: Trigger STK Push + Update dates."""
        logger.info(f"Processing subscription {sub.id} for amount {sub.amount}")
        
        # 1. Trigger STK Push
        # We use a special reference format for recurring: REC-{sub_id}-{timestamp}
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        reference = f"REC-{sub.id}-{timestamp}"
        
        # Call PaymentService (M-Pesa)
        # Note: This sends a prompt to the user's phone.
        result = PaymentService.initiate_stk_push(
            amount=sub.amount,
            phone_number=sub.phone_number,
            account_reference=f"SUB-{sub.id}",
            transaction_desc=f"Recurring Donation for {sub.charity.name}"
        )
        
        if result["success"]:
            # 2. Record Donation as PENDING
            # We treat this as a new donation linked to the subscription
            DonationService.create_donation_after_stk_push(
                checkout_request_id=result["checkout_request_id"],
                merchant_request_id=result["merchant_request_id"],
                donor_id=sub.donor_id,
                charity_id=sub.charity_id,
                amount_cents=sub.amount,
                phone_number=sub.phone_number,
                is_anonymous=sub.is_anonymous,
                is_recurring=True,
                message=f"Recurring donation (Cycle: {timestamp})"
            )
            
            # 3. Update Subscription Dates
            sub.last_run_at = utc_now()
            
            # Calculate next run
            if sub.frequency == "daily":
                sub.next_run_at += timedelta(days=1)
            elif sub.frequency == "weekly":
                sub.next_run_at += timedelta(weeks=1)
            else: # monthly default
                sub.next_run_at += timedelta(days=30)
                
            logger.info(f"Subscription {sub.id} processed successfully. Next run: {sub.next_run_at}")
        else:
            logger.error(f"STK Push failed for subscription {sub.id}: {result.get('error')}")
            # Optional: Retry logic could be added here
