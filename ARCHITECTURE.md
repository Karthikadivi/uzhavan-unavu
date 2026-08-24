# 🏗️ Architecture — Uzhavan Unavu v2.0

## System Overview

Uzhavan Unavu is a **5-layer agentic architecture** designed around the principle of
**"verification over generation"** — the LLM explains, Python computes.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                             │
│                                                                     │
│  Streamlit Web App (Bilingual Tamil/English)                        │
│  ├─ Structured Form Input (dropdowns, sliders)                      │
│  ├─ Natural Language Input (Tamil/English free text)                 │
│  └─ 5-Tab Dashboard: Recommend │ Charts │ Audit │ Pay │ Eval       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                              │
│                                                                     │
│  AgentOrchestrator (agent/orchestrator.py)                          │
│  ├─ State Machine: PARSE → FETCH → COMPUTE → EXPLAIN → PAY        │
│  ├─ Retry Logic: MAX_RETRIES=2 per step                            │
│  ├─ Error Handler: graceful degradation at every step               │
│  └─ Audit Logger: timestamps, inputs, outputs for every tool call   │
└──────┬────────┬──────────┬──────────┬───────────┬──────────────────┘
       │        │          │          │           │
       ▼        ▼          ▼          ▼           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         TOOLS LAYER                                  │
│                                                                     │
│  tool_fetch_prices()    → PriceEngine.get_prices()                  │
│  tool_compute_profits() → ProfitCalculator functions                │
│  tool_check_transport() → TransportChecker.get_best_transport()     │
│  tool_generate_explanation() → Gemini LLM (explain only)            │
│  tool_log_decision()    → AuditEntry creation                       │
└──────┬────────┬──────────┬──────────┬──────────────────────────────┘
       │        │          │          │
       ▼        ▼          ▼          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      COMPUTATION LAYER                               │
│                                                                     │
│  core/price_engine.py      │ Live API fetch + caching + fallback    │
│  core/profit_calculator.py │ Decimal math: revenue, costs, margin   │
│  core/transport_checker.py │ Route feasibility + wastage estimation  │
│  core/models.py            │ Pydantic v2 typed data models           │
└──────┬──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     INTEGRATION LAYER                                │
│                                                                     │
│  data.gov.in API    │ Live mandi commodity prices (JSON)             │
│  Razorpay Test API  │ Payment links, webhooks, settlements           │
│  Google Gemini API  │ Query parsing + result explanation             │
│  Local JSON Cache   │ Fallback prices + settlement records           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow — Single Recommendation

```
User Query: "I have 50kg of jasmine in Madurai"
        │
        ▼
┌─ STEP 1: PARSE_QUERY ──────────────────────────────────┐
│  Input:  "I have 50kg of jasmine in Madurai"            │
│  Tool:   Gemini LLM with QUERY_PARSER_PROMPT            │
│  Output: {commodity: "Jasmine", qty: 50, origin: "Madurai"} │
│  Audit:  ✅ 320ms                                       │
└─────────────────────────────────────┬───────────────────┘
                                      │
                                      ▼
┌─ STEP 2: FETCH_PRICES ─────────────────────────────────┐
│  Input:  commodity="Jasmine", state="Tamil Nadu"        │
│  Tool:   PriceEngine → data.gov.in API                  │
│  Output: [MarketPrice×8] from 8 different mandis        │
│  Fallback: If API fails → cached prices + warning       │
│  Audit:  ✅ 1200ms                                      │
└─────────────────────────────────────┬───────────────────┘
                                      │
                                      ▼
┌─ STEP 3: COMPUTE_PROFITS ──────────────────────────────┐
│  For each market:                                       │
│    revenue = (modal_price / 100) × quantity   [Decimal] │
│    transport = cost_per_kg × quantity          [Decimal] │
│    wastage = revenue × wastage_pct            [Decimal] │
│    net_profit = revenue - transport - wastage  [Decimal] │
│  Sort by net_profit DESC                                │
│  Set confidence based on data freshness                 │
│  Audit:  ✅ 15ms (pure computation, no API call)        │
└─────────────────────────────────────┬───────────────────┘
                                      │
                                      ▼
┌─ STEP 4: GENERATE_EXPLANATION ─────────────────────────┐
│  Input:  Pre-computed profit table + best market         │
│  Tool:   Gemini LLM with EXPLANATION_PROMPT             │
│  Output: Farmer-friendly Tamil/English explanation       │
│  Key:    LLM receives NUMBERS, never computes them      │
│  Audit:  ✅ 2100ms                                      │
└─────────────────────────────────────┬───────────────────┘
                                      │
                                      ▼
┌─ STEP 5: OFFER_PAYMENT (optional) ─────────────────────┐
│  Input:  Best market + net_profit amount                 │
│  Tool:   Razorpay create_payment_link()                 │
│  Output: Payment URL for buyer                          │
│  Audit:  ✅ 800ms                                       │
└─────────────────────────────────────────────────────────┘
```

**Total pipeline latency:** ~4.5s typical (P95 < 8s)

---

## Component Details

### Agent Orchestrator (`agent/orchestrator.py`)

The orchestrator implements a **deterministic state machine** — not a free-form chat loop:

```python
class AgentOrchestrator:
    STEPS = ['PARSE_QUERY', 'FETCH_PRICES', 'COMPUTE_PROFITS',
             'GENERATE_EXPLANATION', 'COMPLETE']
    MAX_RETRIES = 2
```

**Key design decisions:**
- Each step transitions to the next only on success
- Failures trigger retries (up to 2), then fallback, then error
- The agent cannot invent new tools or steps at runtime
- Every step appends to the audit log regardless of outcome

### Price Engine (`core/price_engine.py`)

```
┌─ get_prices(commodity, state) ──────────────────────┐
│                                                      │
│  Try: fetch_live_prices() ──→ data.gov.in API       │
│    │                                                 │
│    ├─ Success → update_cache() → return prices       │
│    │                                                 │
│    └─ Failure (timeout/error/empty)                  │
│         │                                            │
│         └─ Fallback → load from price_cache.json     │
│              │                                       │
│              └─ Check staleness (>24h = warning)     │
└──────────────────────────────────────────────────────┘
```

### Profit Calculator (`core/profit_calculator.py`)

All functions are **pure** — no side effects, no state, no API calls:

```python
# Input:  (price_per_kg=320, quantity=50)
# Output: Decimal("16000.00")
def calculate_revenue(price_per_kg: Decimal, quantity_kg: Decimal) -> Decimal

# Input:  (16000, 2000, 480)
# Output: Decimal("13520.00")
def calculate_net_profit(revenue, transport_cost, wastage_cost) -> Decimal
```

**Why Decimal?**
```python
>>> 0.1 + 0.2          # float
0.30000000000000004     # WRONG for financial math

>>> Decimal('0.1') + Decimal('0.2')  # Decimal
Decimal('0.3')          # CORRECT
```

### Transport Checker (`core/transport_checker.py`)

```
┌─ get_best_transport(origin, dest, qty, perishable) ──┐
│                                                       │
│  1. find_routes(origin, dest) → case-insensitive      │
│  2. For each route:                                   │
│     ├─ Check capacity ≥ quantity                      │
│     ├─ Estimate wastage (if perishable)               │
│     └─ Compute adjusted_cost                          │
│  3. Filter feasible routes                            │
│  4. Return cheapest feasible route                    │
│                                                       │
│  No route found? → Return None (local sale default)   │
└───────────────────────────────────────────────────────┘
```

### Razorpay Integration (`payments/`)

```
┌─ Payment Flow ───────────────────────────────────────┐
│                                                       │
│  1. Agent recommends market + profit amount            │
│  2. Farmer clicks "Generate Payment Link"             │
│  3. FarmerPaymentClient.create_payment_link()          │
│     └─ Razorpay API (test mode) → returns URL         │
│  4. Farmer sends link to buyer                        │
│  5. Buyer pays via Razorpay checkout                  │
│  6. Webhook → WebhookProcessor.process()               │
│     └─ Verify signature → update SettlementTracker     │
│  7. Dashboard shows: ₹ collected, ₹ pending            │
│                                                       │
│  If Razorpay not configured:                          │
│     Payment tab shows setup instructions               │
│     All other features work normally                   │
└───────────────────────────────────────────────────────┘
```

---

## Failure Handling Architecture

Every failure point has an explicit handler:

| Component | Failure Mode | Handler | User Experience |
|-----------|-------------|---------|-----------------|
| data.gov.in API | Timeout (>10s) | Retry 2x → cache fallback | ⚠️ "Using cached prices from [date]" |
| data.gov.in API | Empty results | Cache fallback | ⚠️ "No live data for this crop" |
| Gemini API | Rate limit | Retry with backoff | Brief delay, then response |
| Gemini API | Parse failure | Default extraction | ⚠️ "Could not fully parse query" |
| Transport routes | No route exists | Return None | "Local sale recommended" |
| Transport | Capacity exceeded | Flag infeasible | "Transport limited to Xkg" |
| Razorpay | Not configured | Disable payment tab | "Configure Razorpay to enable payments" |
| Razorpay | API error | Log error, skip payment | "Payment unavailable, recommendation still valid" |
| Unknown crop | Not in database | Ask user to clarify | "Please specify the crop name" |

---

## Evaluation Architecture

```
┌─ Backtest Pipeline ──────────────────────────────────┐
│                                                       │
│  data/synthetic_batch.json (55 scenarios)              │
│       │                                               │
│       ▼                                               │
│  evaluation/backtest.py                               │
│       │                                               │
│       ├─ For each scenario:                           │
│       │   ├─ Run agent.run(query)                     │
│       │   ├─ Record: actual_best_market               │
│       │   ├─ Record: recommended_profit               │
│       │   ├─ Record: local_profit                     │
│       │   ├─ Record: latency_ms                       │
│       │   ├─ Record: handled_gracefully               │
│       │   └─ Record: errors[]                         │
│       │                                               │
│       ▼                                               │
│  evaluation/metrics.py                                │
│       ├─ recommendation_accuracy()  → %               │
│       ├─ average_profit_uplift()    → ₹               │
│       ├─ failure_handling_rate()    → %                │
│       ├─ latency_percentiles()     → P50/P90/P95      │
│       └─ generate_report()         → Markdown + PNGs  │
│                                                       │
│  Output: evaluation/results/                          │
│       ├─ results.json                                 │
│       ├─ report.md                                    │
│       ├─ profit_uplift.png                            │
│       ├─ accuracy_by_category.png                     │
│       └─ latency_histogram.png                        │
└───────────────────────────────────────────────────────┘
```

### Scenario Categories (55 total)

| Category | Count | Tests |
|----------|-------|-------|
| Standard crop/market combos | 20 | Normal workflow |
| High quantity (>200kg) | 8 | Transport capacity limits |
| Perishable goods | 8 | Wastage impact |
| Unknown/misspelled crop | 5 | Error handling |
| No transport available | 5 | Local sale fallback |
| Ambiguous queries | 5 | Partial parsing |
| API failure simulation | 4 | Graceful degradation |

---

## Security Considerations

- API keys stored in `.env` (never committed — in `.gitignore`)
- Razorpay webhook signatures verified with HMAC SHA256
- Payment amounts validated server-side before link generation
- No user data persisted beyond session (Streamlit session state)
- Test mode only — no real money processed

---

## Technology Justification

| Choice | Alternative Considered | Why We Chose This |
|--------|----------------------|-------------------|
| Streamlit | React + FastAPI | Faster prototype, built-in charting, sufficient for demo |
| Gemini Flash | GPT-4, Claude | Cost-effective, good Tamil support, fast inference |
| Pydantic v2 | Dataclasses | Validation, serialization, OpenAPI schema generation |
| Decimal | Float | Exact financial arithmetic (IEEE 754 issues with float) |
| data.gov.in | Scraping | Official API, legal, structured, maintained |
| Razorpay | Stripe | Indian payments leader, buildathon sponsor, test mode |
| Plotly | Matplotlib | Interactive charts in Streamlit, better UX |
| Pytest | Unittest | Cleaner syntax, better fixtures, industry standard |
