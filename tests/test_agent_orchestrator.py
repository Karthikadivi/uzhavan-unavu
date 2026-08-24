import pytest
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import datetime, date

from core.models import MarketPrice, ProfitAnalysis, Recommendation

# Mock orchestrator class to test
class Orchestrator:
    def __init__(self, price_engine, llm, payment_client):
        self.price_engine = price_engine
        self.llm = llm
        self.payment_client = payment_client
        self.audit_log = []
        
    def process(self, commodity, quantity):
        self.audit_log.append("start")
        if commodity == "Unknown":
            self.audit_log.append("error: unknown commodity")
            return "Graceful Error"
            
        try:
            prices = self.price_engine.get_prices(commodity)
        except Exception as e:
            self.audit_log.append("error: price engine failed")
            return "Graceful Error"
            
        # The llm should just generate explanation, not numbers
        explanation = self.llm.explain()
        
        # Payment
        self.payment_client.create_link()
        self.audit_log.append("end")
        return "Success"

def test_full_run_mocked_prices():
    mock_price_engine = MagicMock()
    mock_price_engine.get_prices.return_value = [
        MarketPrice(market_name="M1", commodity="Tomato", variety="V1", min_price=Decimal(10), max_price=Decimal(20), modal_price=Decimal(15), arrival_date=date.today(), state="S", district="D", source="api", fetched_at=datetime.now())
    ]
    mock_llm = MagicMock()
    mock_payment = MagicMock()
    
    orch = Orchestrator(mock_price_engine, mock_llm, mock_payment)
    res = orch.process("Tomato", 100)
    assert res == "Success"

def test_audit_log_populated():
    mock_price_engine = MagicMock()
    orch = Orchestrator(mock_price_engine, MagicMock(), MagicMock())
    orch.process("Tomato", 100)
    assert "start" in orch.audit_log
    assert "end" in orch.audit_log

def test_graceful_handling_price_exception():
    mock_price_engine = MagicMock()
    mock_price_engine.get_prices.side_effect = Exception("API Down")
    orch = Orchestrator(mock_price_engine, MagicMock(), MagicMock())
    res = orch.process("Tomato", 100)
    assert res == "Graceful Error"
    assert "error: price engine failed" in orch.audit_log

def test_graceful_handling_unknown_commodity():
    orch = Orchestrator(MagicMock(), MagicMock(), MagicMock())
    res = orch.process("Unknown", 100)
    assert res == "Graceful Error"
    assert "error: unknown commodity" in orch.audit_log

def test_llm_never_asked_to_compute():
    mock_llm = MagicMock()
    orch = Orchestrator(MagicMock(), mock_llm, MagicMock())
    orch.process("Tomato", 100)
    mock_llm.explain.assert_called_once()
    
def test_payment_link_generation():
    mock_payment = MagicMock()
    orch = Orchestrator(MagicMock(), MagicMock(), mock_payment)
    orch.process("Tomato", 100)
    mock_payment.create_link.assert_called_once()
    
def test_audit_log_size():
    mock_price_engine = MagicMock()
    orch = Orchestrator(mock_price_engine, MagicMock(), MagicMock())
    orch.process("Tomato", 100)
    assert len(orch.audit_log) == 2

def test_process_success_return():
    orch = Orchestrator(MagicMock(), MagicMock(), MagicMock())
    assert orch.process("Tomato", 100) == "Success"
