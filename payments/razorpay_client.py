import os
import logging
import time
from datetime import datetime
from decimal import Decimal

import razorpay # type: ignore

from core.models import PaymentRecord

logger = logging.getLogger(__name__)

class FarmerPaymentClient:
    """Razorpay client for Farmer payments."""

    def __init__(self, key_id: str | None = None, key_secret: str | None = None):
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET")
        self._enabled = bool(self.key_id and self.key_secret)
        self.client = None
        
        if self._enabled:
            try:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                logger.info("Razorpay client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Razorpay client: {e}")
                self._enabled = False
        else:
            logger.warning("Razorpay credentials not found. Payment client disabled.")

    def is_enabled(self) -> bool:
        """Returns whether Razorpay is configured."""
        return self._enabled

    def create_payment_link(
        self,
        amount_inr: Decimal,
        buyer_name: str,
        buyer_contact: str,
        buyer_email: str,
        description: str,
        reference_id: str,
        expire_hours: int = 48
    ) -> PaymentRecord:
        """Creates a Razorpay payment link."""
        if not self._enabled or not self.client:
            logger.warning("Payment client disabled, returning mock payment record.")
            return PaymentRecord(
                payment_link_id=f"plink_mock_{reference_id}",
                amount=amount_inr,
                currency="INR",
                buyer_name=buyer_name,
                description=description,
                status="created",
                created_at=datetime.utcnow(),
                paid_at=None,
                razorpay_payment_id=None
            )

        amount_paise = int(amount_inr * 100)
        expire_by = int(time.time() + expire_hours * 3600)
        
        data = {
            "amount": amount_paise,
            "currency": "INR",
            "accept_partial": False,
            "expire_by": expire_by,
            "reference_id": reference_id,
            "description": description,
            "customer": {
                "name": buyer_name,
                "contact": buyer_contact,
                "email": buyer_email
            },
            "notify": {
                "sms": True,
                "email": True
            },
            "reminder_enable": True,
        }

        try:
            response = self.client.payment_link.create(data)
            logger.info(f"Payment link created successfully: {response.get('id')}")
            return PaymentRecord(
                payment_link_id=response.get('id', ''),
                amount=amount_inr,
                currency=response.get('currency', 'INR'),
                buyer_name=buyer_name,
                description=description,
                status=response.get('status', 'created'),
                created_at=datetime.fromtimestamp(response.get('created_at', time.time())),
                paid_at=None,
                razorpay_payment_id=None
            )
        except Exception as e:
            logger.error(f"Error creating payment link: {e}")
            return PaymentRecord(
                payment_link_id="error",
                amount=amount_inr,
                currency="INR",
                buyer_name=buyer_name,
                description=description,
                status="cancelled",
                created_at=datetime.utcnow(),
                paid_at=None,
                razorpay_payment_id=None
            )

    def check_payment_status(self, payment_link_id: str) -> PaymentRecord:
        """Fetches payment link status from Razorpay API."""
        if not self._enabled or not self.client:
            logger.warning("Payment client disabled, returning mock status check.")
            return PaymentRecord(
                payment_link_id=payment_link_id,
                amount=Decimal('0'),
                currency="INR",
                buyer_name="Unknown",
                description="Status check mock",
                status="created",
                created_at=datetime.utcnow(),
                paid_at=None,
                razorpay_payment_id=None
            )

        try:
            response = self.client.payment_link.fetch(payment_link_id)
            logger.info(f"Fetched payment link status: {response.get('status')}")
            
            paid_at = None
            if response.get('updated_at') and response.get('status') == 'paid':
                paid_at = datetime.fromtimestamp(response.get('updated_at'))
            
            amount_inr = Decimal(str(response.get('amount', 0))) / 100

            return PaymentRecord(
                payment_link_id=response.get('id', payment_link_id),
                amount=amount_inr,
                currency=response.get('currency', 'INR'),
                buyer_name=response.get('customer', {}).get('name', ''),
                description=response.get('description', ''),
                status=response.get('status', 'created'),
                created_at=datetime.fromtimestamp(response.get('created_at', 0)),
                paid_at=paid_at,
                razorpay_payment_id=None # Payment link fetch might not include payment_id immediately
            )
        except Exception as e:
            logger.error(f"Error fetching payment link status: {e}")
            return PaymentRecord(
                payment_link_id=payment_link_id,
                amount=Decimal('0'),
                currency="INR",
                buyer_name="Unknown",
                description="Error fetching status",
                status="cancelled",
                created_at=datetime.utcnow(),
                paid_at=None,
                razorpay_payment_id=None
            )

    def list_payments(self, count: int = 10) -> list[PaymentRecord]:
        """Lists recent payment links."""
        if not self._enabled or not self.client:
            return []
        
        try:
            response = self.client.payment_link.all({"count": count})
            links = response.get('items', [])
            records = []
            
            for link in links:
                amount_inr = Decimal(str(link.get('amount', 0))) / 100
                paid_at = None
                if link.get('updated_at') and link.get('status') == 'paid':
                    paid_at = datetime.fromtimestamp(link.get('updated_at'))
                
                records.append(PaymentRecord(
                    payment_link_id=link.get('id', ''),
                    amount=amount_inr,
                    currency=link.get('currency', 'INR'),
                    buyer_name=link.get('customer', {}).get('name', ''),
                    description=link.get('description', ''),
                    status=link.get('status', 'created'),
                    created_at=datetime.fromtimestamp(link.get('created_at', 0)),
                    paid_at=paid_at,
                    razorpay_payment_id=None
                ))
            return records
        except Exception as e:
            logger.error(f"Error listing payments: {e}")
            return []
