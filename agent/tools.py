import time
from decimal import Decimal
from datetime import datetime
from typing import Any
from core.models import AuditEntry, MarketPrice, ProfitAnalysis, TransportFeasibility


def tool_log_decision(step: str, tool_name: str, inputs: dict[str, Any], outputs: dict[str, Any], duration_ms: int, status: str) -> AuditEntry:
    """Creates an audit log entry."""
    return AuditEntry(
        timestamp=datetime.now(),
        step=step,
        tool_name=tool_name,
        inputs=inputs,
        outputs=outputs,
        duration_ms=duration_ms,
        status=status # type: ignore
    )


def tool_fetch_prices(commodity: str, state: str, price_engine: Any) -> tuple[list[MarketPrice], AuditEntry]:
    """Fetches live market prices. Returns prices and an audit entry."""
    start_time = time.time()
    status = "success"
    prices = []
    
    try:
        prices, warnings = price_engine.get_prices(commodity, state)
        if warnings:
            status = "fallback"
    except Exception as e:
        status = "failure"
        prices = []
    
    duration_ms = int((time.time() - start_time) * 1000)
    audit_entry = tool_log_decision(
        step="FETCH_PRICES",
        tool_name="tool_fetch_prices",
        inputs={"commodity": commodity, "state": state},
        outputs={"prices_count": len(prices)},
        duration_ms=duration_ms,
        status=status
    )
    return prices, audit_entry


def tool_check_transport(origin: str, destination: str, quantity_kg: Decimal, transport_checker: Any) -> tuple[TransportFeasibility | None, AuditEntry]:
    """Checks transport feasibility for a single route."""
    start_time = time.time()
    status = "success"
    feasibility = None
    
    try:
        feasibility = transport_checker.check_route(origin, destination, quantity_kg)
    except Exception as e:
        status = "failure"
    
    duration_ms = int((time.time() - start_time) * 1000)
    audit_entry = tool_log_decision(
        step="CHECK_TRANSPORT",
        tool_name="tool_check_transport",
        inputs={"origin": origin, "destination": destination, "quantity_kg": float(quantity_kg)},
        outputs={"is_feasible": feasibility.is_feasible if feasibility else False},
        duration_ms=duration_ms,
        status=status
    )
    return feasibility, audit_entry


def tool_compute_profits(prices: list[MarketPrice], quantity_kg: Decimal, origin: str, transport_checker: Any, profit_calculator: Any) -> tuple[list[ProfitAnalysis], AuditEntry]:
    """Computes profit analysis for all markets. Returns analyses and audit entry."""
    start_time = time.time()
    status = "success"
    analyses = []
    
    try:
        for price in prices:
            is_local = (price.district.lower() == origin.lower() or price.market_name.lower() == origin.lower())
            
            if is_local:
                analysis = profit_calculator.calculate_local_profit(price, quantity_kg)
                analyses.append(analysis)
            else:
                feasibility = transport_checker.check_route(origin, price.market_name, quantity_kg)
                if feasibility and feasibility.is_feasible:
                    analysis = profit_calculator.calculate_transport_profit(price, quantity_kg, feasibility)
                    analyses.append(analysis)
                    
        # Sort by net_profit descending
        analyses.sort(key=lambda x: x.net_profit, reverse=True)
    except Exception as e:
        status = "failure"
        
    duration_ms = int((time.time() - start_time) * 1000)
    audit_entry = tool_log_decision(
        step="COMPUTE_PROFITS",
        tool_name="tool_compute_profits",
        inputs={"prices_count": len(prices), "quantity_kg": float(quantity_kg), "origin": origin},
        outputs={"analyses_count": len(analyses)},
        duration_ms=duration_ms,
        status=status
    )
    return analyses, audit_entry


def tool_generate_explanation(analyses: list[ProfitAnalysis], warnings: list[str], model: Any, prompt_template: str) -> tuple[str, AuditEntry]:
    """Uses Gemini to generate farmer-friendly explanation of pre-computed results."""
    start_time = time.time()
    status = "success"
    explanation_text = ""
    
    if not analyses:
        status = "failure"
        explanation_text = "No profitable markets found to explain."
    else:
        try:
            best_market = analyses[0]
            profit_table = "Market | Revenue | Transport Cost | Wastage Cost | Net Profit\n"
            profit_table += "---|---|---|---|---\n"
            for a in analyses[:5]: # Top 5
                profit_table += f"{a.market.market_name} | ₹{a.revenue} | ₹{a.transport_cost} | ₹{a.wastage_cost} | ₹{a.net_profit}\n"
            
            prompt = prompt_template.format(
                best_market=f"{best_market.market.market_name} - Net Profit: ₹{best_market.net_profit}",
                confidence="High" if best_market.net_profit > 0 else "Low",
                warnings=", ".join(warnings) if warnings else "None",
                profit_table=profit_table
            )
            
            response = model.generate_content(prompt)
            explanation_text = response.text
        except Exception as e:
            status = "failure"
            explanation_text = "Failed to generate explanation due to an internal error."
            
    duration_ms = int((time.time() - start_time) * 1000)
    audit_entry = tool_log_decision(
        step="GENERATE_EXPLANATION",
        tool_name="tool_generate_explanation",
        inputs={"analyses_count": len(analyses), "warnings_count": len(warnings)},
        outputs={"explanation_length": len(explanation_text)},
        duration_ms=duration_ms,
        status=status
    )
    return explanation_text, audit_entry
