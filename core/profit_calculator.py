from decimal import Decimal, InvalidOperation

from core.models import MarketPrice, ProfitAnalysis, TransportFeasibility


def calculate_revenue(price_per_kg: Decimal, quantity_kg: Decimal) -> Decimal:
    """Calculate total revenue."""
    return price_per_kg * quantity_kg


def calculate_transport_cost(cost_per_kg: Decimal, quantity_kg: Decimal) -> Decimal:
    """Calculate total transport cost."""
    return cost_per_kg * quantity_kg


def calculate_wastage_cost(price_per_kg: Decimal, quantity_kg: Decimal, wastage_pct: Decimal) -> Decimal:
    """Calculate revenue lost to spoilage."""
    wastage_kg = quantity_kg * (wastage_pct / Decimal('100'))
    return price_per_kg * wastage_kg


def calculate_net_profit(revenue: Decimal, transport_cost: Decimal, wastage_cost: Decimal) -> Decimal:
    """Calculate net profit after deducting costs."""
    return revenue - transport_cost - wastage_cost


def calculate_profit_margin(net_profit: Decimal, revenue: Decimal) -> Decimal:
    """Calculate profit margin percentage."""
    if revenue <= 0:
        return Decimal('0')
    return (net_profit / revenue) * Decimal('100')


def analyze_market(market: MarketPrice, quantity_kg: Decimal, transport: TransportFeasibility | None, origin_market: str) -> ProfitAnalysis:
    """Perform full profit analysis for a market."""
    price_per_kg = market.modal_price / Decimal('100')
    revenue = calculate_revenue(price_per_kg, quantity_kg)
    
    is_local = origin_market.lower() == market.market_name.lower()
    
    transport_cost = Decimal('0')
    wastage_cost = Decimal('0')
    
    if transport and transport.is_feasible:
        transport_cost = transport.adjusted_cost
        wastage_cost = price_per_kg * transport.estimated_wastage_kg
        
    net_profit = calculate_net_profit(revenue, transport_cost, wastage_cost)
    profit_margin_pct = calculate_profit_margin(net_profit, revenue)
    
    return ProfitAnalysis(
        market=market,
        revenue=revenue,
        transport_cost=transport_cost,
        wastage_cost=wastage_cost,
        net_profit=net_profit,
        is_local=is_local,
        profit_margin_pct=profit_margin_pct
    )


def rank_markets(analyses: list[ProfitAnalysis]) -> list[ProfitAnalysis]:
    """Sort markets by net profit in descending order."""
    return sorted(analyses, key=lambda x: x.net_profit, reverse=True)


def generate_comparison_table(analyses: list[ProfitAnalysis]) -> list[dict]:
    """Generate a list of dicts for comparison table rendering."""
    return [
        {
            "Market": a.market.market_name,
            "Price/kg": f"₹{a.market.modal_price / Decimal('100'):.2f}",
            "Revenue": f"₹{a.revenue:.2f}",
            "Transport Cost": f"₹{a.transport_cost:.2f}",
            "Wastage Cost": f"₹{a.wastage_cost:.2f}",
            "Net Profit": f"₹{a.net_profit:.2f}",
            "Margin": f"{a.profit_margin_pct:.2f}%",
            "Local": "Yes" if a.is_local else "No"
        }
        for a in analyses
    ]
