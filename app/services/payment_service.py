"""
Payment Service.

Handles M-Pesa Daraja API payment processing for donations using the MpesaClient utility.

This service provides a high-level interface for donation payments and integrates
with the shared M-Pesa utility module for better error handling and logging.
"""
import logging
from app.utils.mpesa import MpesaClient, MpesaError

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for M-Pesa Daraja payment processing."""

    @staticmethod
    def is_configured() -> bool:
        """Check if M-Pesa is properly configured."""
        try:
            # The act of initializing the client validates the config
            MpesaClient()
            return True
        except MpesaError as e:
            logger.warning(f"M-Pesa not configured: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking M-Pesa config: {e}")
            return False

    @staticmethod
    def get_mpesa_access_token() -> str:
        """Get a valid M-Pesa access token."""
        try:
            client = MpesaClient()
            return client.get_access_token()
        except MpesaError as e:
            logger.error(f"Failed to get M-Pesa token: {e}")
            raise RuntimeError(str(e))

    @staticmethod
    def initiate_stk_push(amount: int, phone_number: str, account_reference: str, transaction_desc: str) -> dict:
        """
        Initiate an STK Push payment.
        
        Args:
            amount: Amount in KES
            phone_number: Payer's phone number
            account_reference: Reference for the payment (e.g. Donation ID or Account Name)
            transaction_desc: Short description of the transaction
            
        Returns:
            Dict containing success status and result details
        """
        if not PaymentService.is_configured():
            return {"success": False, "error": "M-Pesa is not configured on this server"}
            
        try:
            client = MpesaClient()
            return client.initiate_stk_push(
                phone=phone_number,
                amount=int(amount),
                reference=account_reference,
                description=transaction_desc
            )
        except MpesaError as e:
            logger.error(f"STK Push failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in STK Push: {e}")
            return {"success": False, "error": "Payment service temporarily unavailable"}

    @staticmethod
    def parse_stk_callback(callback_data: dict) -> dict:
        """
        Parse and validate the STK Push callback data.
        
        Args:
            callback_data: The raw JSON data received from Safaricom
            
        Returns:
            Dict containing parsed fields and success status
        """
        return MpesaClient.parse_callback(callback_data)

    @staticmethod
    def test_connection() -> dict:
        """Test connection by fetching a token."""
        try:
            token = MpesaClient().get_access_token()
            return {"success": True, "token_preview": token[:10] + "..." if token else None}
        except MpesaError as e:
            return {"success": False, "error": str(e)}
