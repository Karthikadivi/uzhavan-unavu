"""
Agent Orchestrator — The core agentic loop for Uzhavan Unavu.

Implements a deterministic state machine:
  PARSE_QUERY → FETCH_PRICES → COMPUTE_PROFITS → GENERATE_EXPLANATION → COMPLETE

Each step has retry logic, graceful degradation, and full audit logging.
"""

import json
import time
import traceback
from decimal import Decimal
from typing import Any
from datetime import datetime

import google.generativeai as genai

from core.models import AgentState, AuditEntry, Recommendation, MarketPrice, ProfitAnalysis
from core.price_engine import PriceEngine
from core.profit_calculator import analyze_market, rank_markets
from core.transport_checker import TransportChecker
from payments.razorpay_client import FarmerPaymentClient
from agent.prompts import SYSTEM_PROMPT, QUERY_PARSER_PROMPT, EXPLANATION_PROMPT, ERROR_EXPLANATION_PROMPT
from agent.tools import (
    tool_fetch_prices,
    tool_compute_profits,
    tool_generate_explanation,
    tool_log_decision
)


class AgentOrchestrator:
    """
    Main agent orchestrator that runs a 5-step state machine:
    PARSE_QUERY → FETCH_PRICES → COMPUTE_PROFITS → GENERATE_EXPLANATION → COMPLETE

    Key properties:
    - All math is done in Python (Decimal) — LLM never computes
    - Every step is logged to an audit trail
    - Retry logic (up to 2 retries) on transient failures
    - Graceful degradation at every step
    """

    STEPS = ['PARSE_QUERY', 'FETCH_PRICES', 'COMPUTE_PROFITS',
             'GENERATE_EXPLANATION', 'COMPLETE']
    MAX_RETRIES = 2

    def __init__(
        self,
        google_api_key: str,
        data_gov_api_key: str | None = None,
        razorpay_key_id: str | None = None,
        razorpay_key_secret: str | None = None
    ):
        """Initialize the orchestrator with API keys. It self-constructs all dependencies."""
        # Initialize Gemini
        genai.configure(api_key=google_api_key)
        self.model = genai.GenerativeModel(
            'gemini-3.6-flash',
            system_instruction=SYSTEM_PROMPT
        )
        self.parser_model = genai.GenerativeModel('gemini-3.6-flash')

        # Initialize core components
        self.price_engine = PriceEngine(api_key=data_gov_api_key)
        self.transport_checker = TransportChecker()
        self.payment_client = FarmerPaymentClient(
            key_id=razorpay_key_id,
            key_secret=razorpay_key_secret
        )

    def run(self, query: str) -> AgentState:
        """Main entry point. Runs the full agent loop and returns final state."""
        state = AgentState(
            query=query,
            commodity=None,
            quantity_kg=None,
            origin=None,
            audit_log=[],
            current_step="PARSE_QUERY",
            prices=[],
            analyses=[],
            recommendation=None,
            payment_link=None,
            errors=[]
        )

        try:
            state = self._parse_query(state)
            if not state.commodity:
                state.errors.append("Could not identify the crop from your query. Please specify the crop name.")
                return state

            state = self._fetch_prices(state)
            if not state.prices:
                return state

            state = self._compute_profits(state)
            if not state.analyses:
                return state

            state = self._generate_explanation(state)

            state.current_step = "COMPLETE"
        except Exception as e:
            state = self._handle_error(state, state.current_step, e)

        return state

    def _parse_query(self, state: AgentState) -> AgentState:
        """Use Gemini to parse natural language query into structured fields."""
        start_time = time.time()
        state.current_step = "PARSE_QUERY"

        for attempt in range(self.MAX_RETRIES):
            try:
                prompt = QUERY_PARSER_PROMPT.format(query=state.query)
                response = self.parser_model.generate_content(prompt)

                # Extract JSON from response
                text = response.text
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(text)

                state.commodity = parsed.get("commodity")
                qty = parsed.get("quantity_kg")
                if qty is not None:
                    state.quantity_kg = Decimal(str(qty))
                state.origin = parsed.get("origin_city")

                duration_ms = int((time.time() - start_time) * 1000)
                state.audit_log.append(tool_log_decision(
                    "PARSE_QUERY", "gemini_parse",
                    {"query": state.query},
                    {"commodity": state.commodity, "quantity_kg": str(state.quantity_kg), "origin": state.origin},
                    duration_ms, "success"
                ))
                return state

            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    state.errors.append(f"Failed to parse query after {self.MAX_RETRIES} retries: {str(e)}")
                    state.audit_log.append(tool_log_decision(
                        "PARSE_QUERY", "gemini_parse",
                        {"query": state.query},
                        {"error": str(e)},
                        int((time.time() - start_time) * 1000), "failure"
                    ))

        return state

    def _fetch_prices(self, state: AgentState) -> AgentState:
        """Fetch live prices using PriceEngine."""
        state.current_step = "FETCH_PRICES"

        if not state.commodity:
            state.errors.append("Cannot fetch prices: commodity not identified.")
            return state

        for attempt in range(self.MAX_RETRIES):
            try:
                prices, audit_entry = tool_fetch_prices(
                    state.commodity, "Tamil Nadu", self.price_engine
                )
                state.audit_log.append(audit_entry)

                if prices:
                    state.prices = prices
                    return state

            except Exception:
                pass

        # If no prices found after retries
        if not state.prices:
            state.errors.append(
                f"Could not fetch prices for '{state.commodity}'. "
                "The market data API may be unavailable or this crop is not in our database."
            )
            state.audit_log.append(tool_log_decision(
                "FETCH_PRICES", "tool_fetch_prices",
                {"commodity": state.commodity},
                {"error": "No prices found after retries"},
                0, "fallback"
            ))

        return state

    def _compute_profits(self, state: AgentState) -> AgentState:
        """Compute profit analysis for all markets using deterministic Python math."""
        state.current_step = "COMPUTE_PROFITS"

        if not state.prices or not state.quantity_kg or not state.origin:
            state.errors.append("Cannot compute profits: missing prices, quantity, or origin.")
            return state

        start_time = time.time()

        try:
            analyses = []
            for price in state.prices:
                # Determine if this is a local market
                is_local = (
                    state.origin.lower() in price.district.lower() or
                    state.origin.lower() in price.market_name.lower()
                )

                if is_local:
                    # Local sale — no transport cost
                    analysis = analyze_market(
                        market=price,
                        quantity_kg=state.quantity_kg,
                        transport=None,
                        origin_market=price.market_name  # force is_local=True
                    )
                    analyses.append(analysis)
                else:
                    # Check transport feasibility
                    feasibility = self.transport_checker.get_best_transport(
                        origin=state.origin,
                        destination=price.district,
                        quantity_kg=state.quantity_kg
                    )
                    # Include even if no transport — shows as infeasible
                    analysis = analyze_market(
                        market=price,
                        quantity_kg=state.quantity_kg,
                        transport=feasibility,
                        origin_market=state.origin
                    )
                    analyses.append(analysis)

            # Rank by net profit
            analyses = rank_markets(analyses)

            duration_ms = int((time.time() - start_time) * 1000)
            state.audit_log.append(tool_log_decision(
                "COMPUTE_PROFITS", "profit_calculator",
                {"prices_count": len(state.prices), "quantity_kg": str(state.quantity_kg), "origin": state.origin},
                {"analyses_count": len(analyses), "best_profit": str(analyses[0].net_profit) if analyses else "0"},
                duration_ms, "success"
            ))

            if analyses:
                state.analyses = analyses
                best_analysis = analyses[0]

                # Determine confidence
                warnings = []
                has_fallback_data = any(p.source == 'fallback' for p in state.prices)
                if has_fallback_data:
                    warnings.append("⚠️ Using cached price data — live market data was unavailable.")

                if best_analysis.net_profit <= 0:
                    warnings.append("Best market still results in a loss. Consider waiting for better prices.")
                    confidence = "low"
                elif has_fallback_data:
                    confidence = "medium"
                elif len(analyses) < 3:
                    confidence = "medium"
                else:
                    confidence = "high"

                state.recommendation = Recommendation(
                    best_market=best_analysis,
                    all_analyses=analyses,
                    explanation="",  # Will be filled by _generate_explanation
                    confidence=confidence,
                    warnings=warnings
                )
            else:
                state.errors.append("No profitable markets found for your produce.")

        except Exception as e:
            state.errors.append(f"Profit computation error: {str(e)}")
            state.audit_log.append(tool_log_decision(
                "COMPUTE_PROFITS", "profit_calculator",
                {"prices_count": len(state.prices)},
                {"error": str(e)},
                int((time.time() - start_time) * 1000), "failure"
            ))

        return state

    def _generate_explanation(self, state: AgentState) -> AgentState:
        """Generate farmer-friendly explanation of pre-computed results."""
        state.current_step = "GENERATE_EXPLANATION"

        if not state.recommendation or not state.analyses:
            state.errors.append("No recommendation available to explain.")
            return state

        explanation, audit_entry = tool_generate_explanation(
            state.analyses,
            state.recommendation.warnings,
            self.model,
            EXPLANATION_PROMPT
        )
        state.audit_log.append(audit_entry)

        if audit_entry.status == "success":
            state.recommendation.explanation = explanation
        else:
            # Provide a basic fallback explanation
            best = state.recommendation.best_market
            state.recommendation.explanation = (
                f"**Recommended:** Sell at {best.market.market_name}\n\n"
                f"- Revenue: ₹{best.revenue:.2f}\n"
                f"- Transport Cost: ₹{best.transport_cost:.2f}\n"
                f"- Net Profit: ₹{best.net_profit:.2f}\n\n"
                f"*Detailed explanation unavailable — showing raw numbers.*"
            )

        return state

    def _handle_error(self, state: AgentState, step: str, error: Exception) -> AgentState:
        """Graceful error handling with audit logging."""
        error_msg = f"{type(error).__name__}: {str(error)}"
        state.errors.append(f"Unexpected error in {step}: {str(error)}")

        state.audit_log.append(tool_log_decision(
            step, "error_handler",
            {},
            {"error": error_msg, "traceback": traceback.format_exc()},
            0, "failure"
        ))

        # Try to generate a friendly error message
        try:
            prompt = ERROR_EXPLANATION_PROMPT.format(error_details=str(error))
            response = self.model.generate_content(prompt)
            state.errors.append(f"💡 {response.text}")
        except Exception:
            pass

        return state

    def generate_payment_link(
        self,
        state: AgentState,
        buyer_name: str,
        buyer_contact: str,
        buyer_email: str
    ) -> AgentState:
        """Generate a Razorpay payment link for the recommended sale."""
        if not state.recommendation or not state.recommendation.best_market:
            state.errors.append("No recommendation available. Run a query first.")
            return state

        if not self.payment_client.is_enabled():
            state.errors.append("Razorpay is not configured. Add API keys to .env file.")
            return state

        amount_inr = state.recommendation.best_market.net_profit
        start_time = time.time()

        try:
            reference_id = f"UU-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            description = f"Uzhavan Unavu - Sale of {state.quantity_kg}kg {state.commodity}"

            record = self.payment_client.create_payment_link(
                amount_inr=amount_inr,
                buyer_name=buyer_name,
                buyer_contact=buyer_contact,
                buyer_email=buyer_email,
                description=description,
                reference_id=reference_id
            )

            state.payment_link = record.payment_link_id
            duration_ms = int((time.time() - start_time) * 1000)

            state.audit_log.append(tool_log_decision(
                "PAYMENT", "generate_payment_link",
                {"amount": str(amount_inr), "buyer": buyer_name},
                {"payment_link_id": record.payment_link_id, "status": record.status},
                duration_ms, "success"
            ))

        except Exception as e:
            state.errors.append(f"Payment link error: {str(e)}")
            state.audit_log.append(tool_log_decision(
                "PAYMENT", "generate_payment_link",
                {"amount": str(amount_inr)},
                {"error": str(e)},
                int((time.time() - start_time) * 1000), "failure"
            ))

        return state

    def get_audit_log(self, state: AgentState) -> list[dict]:
        """Returns the audit log as a list of dicts for display."""
        return [entry.model_dump() for entry in state.audit_log]
