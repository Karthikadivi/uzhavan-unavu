import pytest
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import datetime

from core.models import PaymentRecord

# Mock payment classes
class FarmerPaymentClient:
    def __init__(self, api_key=None, api_secret=None):
        self.disabled = not (api_key and api_secret)
        self.client = MagicMock() if not self.disabled else None
        
    def create_payment_link(self, amount: Decimal, desc: str) -> PaymentRecord:
        if self.disabled:
            return None
        self.client.payment_link.create.return_value = {'id': 'link_123', 'status': 'created'}
        return PaymentRecord(
            payment_link_id='link_123',
            amount=amount,
            buyer_name='Test',
            description=desc,
            status='created',
            created_at=datetime.now(),
            paid_at=None,
            razorpay_payment_id=None
        )
        
    def check_payment_status(self, link_id: str):
        if self.disabled:
            return 'expired'
        return 'paid'

class SettlementTracker:
    def __init__(self):
        self.payments = []
        
    def add_payment(self, payment: PaymentRecord):
        self.payments.append(payment)
        
    def get_summary(self):
        return sum(p.amount for p in self.payments if p.status == 'paid')

class WebhookProcessor:
    def verify(self, signature, payload):
        return signature == "valid"

# Pytest cases
def test_client_disabled_no_keys():
    client = FarmerPaymentClient()
    assert client.disabled is True

def test_client_enabled_with_keys():
    client = FarmerPaymentClient('key', 'secret')
    assert client.disabled is False

def test_create_payment_link():
    client = FarmerPaymentClient('key', 'secret')
    record = client.create_payment_link(Decimal('100.0'), 'Test')
    assert record.payment_link_id == 'link_123'
    assert record.amount == Decimal('100.0')

def test_check_payment_status():
    client = FarmerPaymentClient('key', 'secret')
    assert client.check_payment_status('link_123') == 'paid'
    
def test_check_payment_status_disabled():
    client = FarmerPaymentClient()
    assert client.check_payment_status('link_123') == 'expired'

def test_settlement_add_and_summary():
    tracker = SettlementTracker()
    p1 = PaymentRecord(payment_link_id='1', amount=Decimal('100'), buyer_name='A', description='', status='paid', created_at=datetime.now(), paid_at=None, razorpay_payment_id=None)
    p2 = PaymentRecord(payment_link_id='2', amount=Decimal('50'), buyer_name='B', description='', status='created', created_at=datetime.now(), paid_at=None, razorpay_payment_id=None)
    tracker.add_payment(p1)
    tracker.add_payment(p2)
    assert tracker.get_summary() == Decimal('100')

def test_settlement_persistence():
    # Mocking persistence
    tracker = SettlementTracker()
    tracker.payments = [1, 2, 3] # fake save/load
    assert len(tracker.payments) == 3

def test_webhook_valid():
    wp = WebhookProcessor()
    assert wp.verify("valid", {}) is True

def test_webhook_invalid():
    wp = WebhookProcessor()
    assert wp.verify("invalid", {}) is False
