"""
Donation Service.

Business logic for donation-related operations with M-Pesa payment integration.
"""
import logging

from app.extensions import db
from app.models.donation import Donation, DonationStatus
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)


class DonationService:
    """Service class for donation operations."""

    # ── M-Pesa donation flow ────────────────────────────────────────────

    @staticmethod
    def initiate_mpesa_donation(
        donor_id, charity_id, amount_kes, phone_number,
        is_anonymous=False, message=None, account_reference="SheNeeds",
    ):
        if amount_kes <= 0:
            raise ValueError("Amount must be a positive number")

        amount_cents = int(amount_kes * 100)

        stk = PaymentService.initiate_stk_push(
            amount=int(amount_kes),
            phone_number=phone_number,
            account_reference=account_reference,
            transaction_desc=f"Donation to {account_reference}",
        )

        if not stk["success"]:
            raise ValueError(stk.get("error", "STK Push initiation failed"))

        donation = Donation(
            amount=amount_cents,
            donor_id=donor_id,
            charity_id=charity_id,
            phone_number=phone_number,
            status=DonationStatus.PENDING,
            checkout_request_id=stk["checkout_request_id"],
            merchant_request_id=stk["merchant_request_id"],
            is_anonymous=is_anonymous,
            message=message,
        )
        db.session.add(donation)
        db.session.commit()

        logger.info(
            "PENDING donation #%d created (checkout=%s)",
            donation.id, stk["checkout_request_id"],
        )

        return {
            "donation": donation,
            "checkout_request_id": stk["checkout_request_id"],
            "customer_message": stk.get("customer_message", ""),
        }

    # ── Callback processing ─────────────────────────────────────────────

    @staticmethod
    def process_stk_callback(callback_data):
        parsed = PaymentService.parse_stk_callback(callback_data)
        checkout_id = parsed.get("checkout_request_id")

        if not checkout_id:
            return {"success": False, "error": "Missing CheckoutRequestID in callback"}

        donation = Donation.query.filter_by(checkout_request_id=checkout_id).first()
        if not donation:
            logger.warning("No donation found for checkout_request_id=%s", checkout_id)
            return {"success": False, "error": "No matching donation found"}

        if donation.status in (DonationStatus.SUCCESS, DonationStatus.FAILED):
            logger.info(
                "Donation #%d already %s — ignoring duplicate callback",
                donation.id, donation.status,
            )
            return {
                "success": True,
                "already_processed": True,
                "donation_id": donation.id,
                "donation_status": donation.status,
            }

        if parsed["success"]:
            donation.status = DonationStatus.SUCCESS
            donation.mpesa_receipt_number = parsed.get("mpesa_receipt_number")
            logger.info(
                "Donation #%d marked SUCCESS (receipt=%s)",
                donation.id, donation.mpesa_receipt_number
            )
        else:
            donation.status = DonationStatus.FAILED
            donation.failure_reason = parsed.get("error", "Payment was not completed")
            logger.warning(
                "Donation #%d marked FAILED: %s", donation.id, donation.failure_reason,
            )

        db.session.commit()

        return {
            "success": True,
            "donation_id": donation.id,
            "donation_status": donation.status,
            "mpesa_receipt_number": donation.mpesa_receipt_number,
        }

    # ── Simple donation flow ────────────────────────────────────────────

    @staticmethod
    def create_donation(donor_id, charity_id, amount_cents, is_anonymous=False,
                        is_recurring=False, message=None):
        donation = Donation(
            amount=amount_cents,
            donor_id=donor_id,
            charity_id=charity_id,
            is_anonymous=is_anonymous,
            is_recurring=is_recurring,
            message=message,
            status=DonationStatus.SUCCESS,
        )
        db.session.add(donation)
        db.session.commit()
        return donation

    # ── Query helpers ───────────────────────────────────────────────────

    @staticmethod
    def get_donation(donation_id):
        return Donation.query.get(donation_id)

    @staticmethod
    def get_donation_by_checkout(checkout_request_id):
        return Donation.query.filter_by(checkout_request_id=checkout_request_id).first()

    @staticmethod
    def get_donations_by_donor(donor_id, limit=None):
        query = Donation.query.filter_by(donor_id=donor_id).order_by(
            Donation.created_at.desc()
        )
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @staticmethod
    def get_donations_by_charity(charity_id, limit=None):
        query = Donation.query.filter_by(
            charity_id=charity_id,
            status=DonationStatus.SUCCESS,
        ).order_by(Donation.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @staticmethod
    def get_donor_stats(donor_id):
        successful = Donation.query.filter_by(donor_id=donor_id, status=DonationStatus.SUCCESS)

        total_donated = db.session.query(
            db.func.coalesce(db.func.sum(Donation.amount), 0)
        ).filter(
            Donation.donor_id == donor_id,
            Donation.status == DonationStatus.SUCCESS,
        ).scalar() or 0

        donation_count = successful.count()

        unique_charities = db.session.query(
            db.func.count(db.func.distinct(Donation.charity_id))
        ).filter(
            Donation.donor_id == donor_id,
            Donation.status == DonationStatus.SUCCESS,
        ).scalar() or 0

        active_recurring = Donation.query.filter_by(donor_id=donor_id, is_recurring=True).count()

        return {
            "total_donated": total_donated,
            "total_donated_dollars": total_donated / 100,
            "donation_count": donation_count,
            "charities_supported": unique_charities,
            "active_recurring": active_recurring,
        }

    @staticmethod
    def get_total_donations_amount():
        result = db.session.query(
            db.func.coalesce(db.func.sum(Donation.amount), 0)
        ).filter(Donation.status == DonationStatus.SUCCESS).scalar()
        return result or 0

    @staticmethod
    def get_total_donation_count():
        return Donation.query.filter_by(status=DonationStatus.SUCCESS).count()

    @staticmethod
    def get_recurring_donations(donor_id):
        return Donation.query.filter_by(donor_id=donor_id, is_recurring=True).all()
