from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketPrice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market_name: str
    commodity: str
    variety: str
    min_price: Decimal
    max_price: Decimal
    modal_price: Decimal
    unit: str = "Quintal"
    arrival_date: date
    state: str
    district: str
    source: Literal['api', 'cache', 'fallback']
    fetched_at: datetime


class TransportRoute(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    origin: str
    destination: str
    distance_km: float
    cost_per_kg: Decimal
    capacity_kg: int
    travel_time_hours: float
    partner_name: str
    contact: str
    perishable_wastage_pct: Decimal


class TransportFeasibility(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    route: TransportRoute
    is_feasible: bool
    reason: str
    adjusted_cost: Decimal
    estimated_wastage_kg: Decimal


class ProfitAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market: MarketPrice
    revenue: Decimal
    transport_cost: Decimal
    wastage_cost: Decimal
    net_profit: Decimal
    is_local: bool
    profit_margin_pct: Decimal


class Recommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    best_market: ProfitAnalysis
    all_analyses: list[ProfitAnalysis]
    explanation: str
    confidence: Literal['high', 'medium', 'low']
    warnings: list[str]


class AuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    step: str
    tool_name: str
    inputs: dict
    outputs: dict
    duration_ms: int
    status: Literal['success', 'failure', 'fallback']


class AgentState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: str
    commodity: str | None = None
    quantity_kg: Decimal | None = None
    origin: str | None = None
    audit_log: list[AuditEntry] = Field(default_factory=list)
    current_step: str = "initialized"
    prices: list[MarketPrice] = Field(default_factory=list)
    analyses: list[ProfitAnalysis] = Field(default_factory=list)
    recommendation: Recommendation | None = None
    payment_link: str | None = None
    errors: list[str] = Field(default_factory=list)


class PaymentRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_link_id: str
    amount: Decimal
    currency: str = "INR"
    buyer_name: str
    description: str
    status: Literal['created', 'paid', 'expired', 'cancelled']
    created_at: datetime
    paid_at: datetime | None = None
    razorpay_payment_id: str | None = None
