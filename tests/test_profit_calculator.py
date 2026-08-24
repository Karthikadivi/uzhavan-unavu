"""
Unit tests for core/profit_calculator.py

Tests all deterministic computation functions using known input/output pairs.
All math uses Decimal for exact financial arithmetic.
"""

import pytest
from decimal import Decimal
from datetime import datetime, date

from core.models import MarketPrice, ProfitAnalysis, TransportFeasibility, TransportRoute
from core.profit_calculator import (
    calculate_revenue,
    calculate_transport_cost,
    calculate_wastage_cost,
    calculate_net_profit,
    calculate_profit_margin,
    analyze_market,
    rank_markets,
    generate_comparison_table,
)


# --- Helper to create a MarketPrice for tests ---
def _make_market(name: str = "Test Market", modal_price: Decimal = Decimal("32000")) -> MarketPrice:
    return MarketPrice(
        market_name=name,
        commodity="Jasmine",
        variety="Madurai Malli",
        min_price=Decimal("28000"),
        max_price=Decimal("35000"),
        modal_price=modal_price,
        unit="Quintal",
        arrival_date=date.today(),
        state="Tamil Nadu",
        district="Madurai",
        source="api",
        fetched_at=datetime.now(),
    )


def _make_transport(cost_per_kg: Decimal = Decimal("5"), wastage_kg: Decimal = Decimal("2.5")) -> TransportFeasibility:
    route = TransportRoute(
        origin="Madurai",
        destination="Chennai",
        distance_km=462,
        cost_per_kg=cost_per_kg,
        capacity_kg=500,
        travel_time_hours=8.0,
        partner_name="Test Transport",
        contact="9876543210",
        perishable_wastage_pct=Decimal("5"),
    )
    return TransportFeasibility(
        route=route,
        is_feasible=True,
        reason="Route is feasible",
        adjusted_cost=cost_per_kg * Decimal("50"),
        estimated_wastage_kg=wastage_kg,
    )


# --- Revenue Tests ---
class TestCalculateRevenue:
    def test_basic(self):
        assert calculate_revenue(Decimal("320"), Decimal("50")) == Decimal("16000")

    def test_zero_quantity(self):
        assert calculate_revenue(Decimal("320"), Decimal("0")) == Decimal("0")

    def test_zero_price(self):
        assert calculate_revenue(Decimal("0"), Decimal("50")) == Decimal("0")

    def test_large_numbers(self):
        assert calculate_revenue(Decimal("1000"), Decimal("1000")) == Decimal("1000000")

    def test_decimal_precision(self):
        result = calculate_revenue(Decimal("33.33"), Decimal("3"))
        assert result == Decimal("99.99")


# --- Transport Cost Tests ---
class TestCalculateTransportCost:
    def test_basic(self):
        assert calculate_transport_cost(Decimal("5"), Decimal("50")) == Decimal("250")

    def test_zero_cost(self):
        assert calculate_transport_cost(Decimal("0"), Decimal("50")) == Decimal("0")

    def test_zero_quantity(self):
        assert calculate_transport_cost(Decimal("5"), Decimal("0")) == Decimal("0")


# --- Wastage Cost Tests ---
class TestCalculateWastageCost:
    def test_basic(self):
        # 5% wastage on 100kg at ₹320/kg = 5kg * 320 = ₹1600
        result = calculate_wastage_cost(Decimal("320"), Decimal("100"), Decimal("5"))
        assert result == Decimal("1600.00")

    def test_zero_wastage(self):
        assert calculate_wastage_cost(Decimal("320"), Decimal("100"), Decimal("0")) == Decimal("0.00")

    def test_full_wastage(self):
        result = calculate_wastage_cost(Decimal("320"), Decimal("100"), Decimal("100"))
        assert result == Decimal("32000.00")


# --- Net Profit Tests ---
class TestCalculateNetProfit:
    def test_basic(self):
        assert calculate_net_profit(Decimal("16000"), Decimal("250"), Decimal("480")) == Decimal("15270")

    def test_zero_costs(self):
        assert calculate_net_profit(Decimal("16000"), Decimal("0"), Decimal("0")) == Decimal("16000")

    def test_negative_profit(self):
        assert calculate_net_profit(Decimal("100"), Decimal("200"), Decimal("50")) == Decimal("-150")

    def test_all_zero(self):
        assert calculate_net_profit(Decimal("0"), Decimal("0"), Decimal("0")) == Decimal("0")


# --- Profit Margin Tests ---
class TestCalculateProfitMargin:
    def test_basic(self):
        assert calculate_profit_margin(Decimal("500"), Decimal("1000")) == Decimal("50")

    def test_zero_revenue(self):
        """Division by zero should return 0, not crash."""
        assert calculate_profit_margin(Decimal("500"), Decimal("0")) == Decimal("0")

    def test_negative_margin(self):
        result = calculate_profit_margin(Decimal("-100"), Decimal("1000"))
        assert result == Decimal("-10")

    def test_hundred_percent(self):
        assert calculate_profit_margin(Decimal("1000"), Decimal("1000")) == Decimal("100")


# --- Analyze Market Tests ---
class TestAnalyzeMarket:
    def test_local_market(self):
        """Local sale = no transport, no wastage."""
        market = _make_market("Madurai Market", Decimal("32000"))
        analysis = analyze_market(market, Decimal("50"), transport=None, origin_market="Madurai Market")
        assert analysis.is_local is True
        assert analysis.transport_cost == Decimal("0")
        assert analysis.wastage_cost == Decimal("0")
        # Revenue = 32000/100 * 50 = 16000
        assert analysis.revenue == Decimal("16000")
        assert analysis.net_profit == Decimal("16000")

    def test_distant_market_with_transport(self):
        """Distant market includes transport + wastage costs."""
        market = _make_market("Chennai Market", Decimal("40000"))
        transport = _make_transport(cost_per_kg=Decimal("5"), wastage_kg=Decimal("2.5"))
        analysis = analyze_market(market, Decimal("50"), transport=transport, origin_market="Madurai")
        assert analysis.is_local is False
        # Revenue = 40000/100 * 50 = 20000
        assert analysis.revenue == Decimal("20000")
        # Transport = 5*50 = 250
        assert analysis.transport_cost == Decimal("250")


# --- Rank Markets Tests ---
class TestRankMarkets:
    def test_sorts_descending(self):
        m1 = _make_market("Market A", Decimal("20000"))
        m2 = _make_market("Market B", Decimal("40000"))
        a1 = analyze_market(m1, Decimal("50"), None, "Market A")
        a2 = analyze_market(m2, Decimal("50"), None, "Market B")
        ranked = rank_markets([a1, a2])
        assert ranked[0].net_profit > ranked[1].net_profit

    def test_single_market(self):
        m = _make_market("Only Market")
        a = analyze_market(m, Decimal("50"), None, "Only Market")
        ranked = rank_markets([a])
        assert len(ranked) == 1

    def test_empty_list(self):
        assert rank_markets([]) == []


# --- Comparison Table Tests ---
class TestGenerateComparisonTable:
    def test_returns_list_of_dicts(self):
        m = _make_market()
        a = analyze_market(m, Decimal("50"), None, "Test Market")
        table = generate_comparison_table([a])
        assert isinstance(table, list)
        assert len(table) == 1
        assert "Market" in table[0]
        assert "Net Profit" in table[0]
        assert "Revenue" in table[0]
