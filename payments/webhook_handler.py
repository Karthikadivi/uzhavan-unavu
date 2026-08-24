import json
import hmac
import hashlib
import logging
from decimal import Decimal
from datetime import datetime
from typing import Any

from core.models import PaymentRecord
from payments.settlement_tracker import SettlementTracker

logger = logging.getLogger(__name__)

def verify_webhook_signature(body: str, signature: str, secret: str) -> bool:
    """HMAC SHA256 verification of Razorpay webhook payload."""
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False

def parse_payment_event(payload: dict[str, Any]) -> PaymentRecord | None:
    """Parses 'payment_link.paid' events into PaymentRecord objects."""
    try:
        event = payload.get("event")
        if event != "payment_link.paid":
            logger.info(f"Ignoring unhandled event type: {event}")
            return None

        payment_link = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        
        if not payment_link:
            logger.error("No payment_link entity found in payload.")
            return None

        payment_link_id = payment_link.get("id")
        amount = Decimal(str(payment_link.get("amount", 0))) / 100
        currency = payment_link.get("currency", "INR")
        buyer_name = payment_link.get("customer", {}).get("name", "")
        description = payment_link.get("description", "")
        status = payment_link.get("status", "created")
        
        created_at_ts = payment_link.get("created_at", 0)
        created_at = datetime.fromtimestamp(created_at_ts) if created_at_ts else datetime.utcnow()
        
        paid_at = None
        updated_at_ts = payment_link.get("updated_at")
        if updated_at_ts and status == "paid":
            paid_at = datetime.fromtimestamp(updated_at_ts)
            
        razorpay_payment_id = payment.get("id") if payment else None

        return PaymentRecord(
            payment_link_id=payment_link_id,
            amount=amount,
            currency=currency,
            buyer_name=buyer_name,
            description=description,
            status=status,
            created_at=created_at,
            paid_at=paid_at,
            razorpay_payment_id=razorpay_payment_id
        )
    except Exception as e:
        logger.error(f"Error parsing payment event: {e}")
        return None

class WebhookProcessor:
    """Processes incoming Razorpay webhooks."""
    
    def __init__(self, secret: str, tracker: SettlementTracker):
        self.secret = secret
        self.tracker = tracker

    def process(self, body: str, signature: str) -> dict[str, Any]:
        """Verifies signature, parses event, updates tracker, returns response dict with status."""
        if not verify_webhook_signature(body, signature, self.secret):
            logger.warning("Invalid webhook signature.")
            return {"status": "error", "message": "Invalid signature", "code": 401}

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Malformed JSON payload.")
            return {"status": "error", "message": "Malformed payload", "code": 400}

        record = parse_payment_event(payload)
        if record and record.status == "paid":
            self.tracker.update_status(
                payment_link_id=record.payment_link_id,
                status=record.status,
                razorpay_payment_id=record.razorpay_payment_id,
                paid_at=record.paid_at
            )
            logger.info(f"Payment {record.payment_link_id} marked as paid.")
            return {"status": "success", "message": "Payment updated", "code": 200}
        
        return {"status": "success", "message": "Event ignored or unhandled", "code": 200}
