import json
import os
import threading
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from core.models import PaymentRecord

logger = logging.getLogger(__name__)

class SettlementTracker:
    """Tracks payment settlements and persists to JSON."""
    
    def __init__(self, db_path: str = 'data/settlements.json'):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.payments: dict[str, PaymentRecord] = {}
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        
        records = self._load()
        for record in records:
            self.payments[record.payment_link_id] = record

    def add_payment(self, record: PaymentRecord) -> None:
        """Adds a new payment record."""
        with self._lock:
            self.payments[record.payment_link_id] = record
            self._save()
            
    def update_status(
        self,
        payment_link_id: str,
        status: str,
        razorpay_payment_id: str | None = None,
        paid_at: datetime | None = None
    ) -> None:
        """Updates payment status."""
        with self._lock:
            record = self.payments.get(payment_link_id)
            if record:
                record.status = status # type: ignore
                if razorpay_payment_id:
                    record.razorpay_payment_id = razorpay_payment_id
                if paid_at:
                    record.paid_at = paid_at
                self._save()
            else:
                logger.warning(f"Payment record {payment_link_id} not found for update.")

    def get_payment(self, payment_link_id: str) -> PaymentRecord | None:
        """Retrieves a payment record by ID."""
        with self._lock:
            return self.payments.get(payment_link_id)

    def get_all_payments(self) -> list[PaymentRecord]:
        """Retrieves all payment records."""
        with self._lock:
            return list(self.payments.values())

    def get_summary(self) -> dict[str, Any]:
        """Returns summary statistics of payments."""
        with self._lock:
            total_created = 0
            total_paid = 0
            total_pending = 0
            total_expired = 0
            amount_collected = Decimal('0')
            amount_pending = Decimal('0')
            
            for record in self.payments.values():
                total_created += 1
                if record.status == 'paid':
                    total_paid += 1
                    amount_collected += record.amount
                elif record.status == 'expired':
                    total_expired += 1
                else:
                    total_pending += 1
                    amount_pending += record.amount
                    
            return {
                "total_created": total_created,
                "total_paid": total_paid,
                "total_pending": total_pending,
                "total_expired": total_expired,
                "amount_collected": amount_collected,
                "amount_pending": amount_pending
            }

    def _save(self) -> None:
        """Persists to JSON file."""
        data = []
        for record in self.payments.values():
            data.append({
                "payment_link_id": record.payment_link_id,
                "amount": str(record.amount),
                "currency": record.currency,
                "buyer_name": record.buyer_name,
                "description": record.description,
                "status": record.status,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "paid_at": record.paid_at.isoformat() if record.paid_at else None,
                "razorpay_payment_id": record.razorpay_payment_id
            })
            
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settlements to {self.db_path}: {e}")

    def _load(self) -> list[PaymentRecord]:
        """Loads from JSON file."""
        if not os.path.exists(self.db_path):
            return []
            
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            records = []
            for item in data:
                created_at_str = item.get("created_at")
                paid_at_str = item.get("paid_at")
                
                created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()
                paid_at = datetime.fromisoformat(paid_at_str) if paid_at_str else None
                
                record = PaymentRecord(
                    payment_link_id=item.get("payment_link_id", ""),
                    amount=Decimal(item.get("amount", "0")),
                    currency=item.get("currency", "INR"),
                    buyer_name=item.get("buyer_name", ""),
                    description=item.get("description", ""),
                    status=item.get("status", "created"), # type: ignore
                    created_at=created_at,
                    paid_at=paid_at,
                    razorpay_payment_id=item.get("razorpay_payment_id")
                )
                records.append(record)
            return records
        except json.JSONDecodeError:
            logger.error(f"Corrupt JSON file at {self.db_path}.")
            return []
        except Exception as e:
            logger.error(f"Error loading settlements from {self.db_path}: {e}")
            return []
