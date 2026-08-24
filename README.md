# 🌾 Uzhavan Unavu — AI-Powered Market Intelligence Agent

**An agentic AI system that helps Tamil Nadu farmers maximize produce income through real-time market intelligence, deterministic profit computation, and integrated digital payments.**

> Built for the **Razorpay AI Buildathon 2026** | Track: Open

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)
![Razorpay](https://img.shields.io/badge/Razorpay-Test_Mode-purple)
![Tests](https://img.shields.io/badge/Tests-50+-green)

---

## 🎯 The Problem

Small-hold farmers in Tamil Nadu lose **20-40% of potential income** due to two compounding problems:

1. **Information Asymmetry:** Farmers don't know which mandi pays best for their crop today. They sell to local middlemen at below-market rates because checking 25+ markets across the state is impossible manually.

2. **Settlement Friction:** Cash-based transactions with unknown buyers are risky. Delayed payments, disputes, and trust issues prevent farmers from selling to higher-paying distant markets.

**Impact:** India has 12.56 crore agricultural households. Even a ₹5/kg improvement on a 100kg sale = ₹500 more per transaction. Across millions of daily transactions, this is billions in recoverable farmer income.

---

## ✨ Our Solution

Uzhavan Unavu is a **production-grade agentic AI system** — not a prompt wrapper. It combines:

| Layer | What It Does | Why It Matters |
|-------|-------------|----------------|
| 🤖 **Agent Orchestrator** | 5-tool state machine with retry logic and audit trail | Bounded, explainable, failure-resilient |
| 🧮 **Deterministic Engine** | All math in Python `Decimal` — LLM never computes | Verifiable, reproducible numbers |
| 📡 **Live Data** | Real mandi prices from data.gov.in API | Not hardcoded — reflects today's market |
| 💳 **Razorpay Payments** | Payment links for farmer→buyer settlement | Digital trust layer for distant sales |
| 📊 **Evaluation Suite** | 55 backtested scenarios with measured metrics | Proof of accuracy, not cherry-picked demos |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                        │
│  Bilingual UI (Tamil/English) │ Structured + NL Input        │
│  5 Tabs: Recommendation │ Charts │ Audit Log │ Pay │ Eval   │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                   AGENT ORCHESTRATOR                         │
│  State Machine: PARSE → FETCH → COMPUTE → EXPLAIN → PAY     │
│  Retry logic (2x) │ Graceful degradation │ Decision log      │
└──────┬────────┬──────────┬──────────┬───────────┬───────────┘
       │        │          │          │           │
       ▼        ▼          ▼          ▼           ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
   │ TOOL 1 │ │ TOOL 2 │ │ TOOL 3 │ │  TOOL 4  │ │  TOOL 5  │
   │ Fetch  │ │Compute │ │Check   │ │ Generate │ │  Log &   │
   │ Prices │ │ Profit │ │Transprt│ │ Pay Link │ │  Audit   │
   │(API)   │ │(Decimal│ │(Rules) │ │(Razorpay)│ │ (JSON)   │
   └───┬────┘ └────────┘ └────────┘ └────┬─────┘ └──────────┘
       │                                  │
       ▼                                  ▼
  data.gov.in                      Razorpay Test API
  (Live Mandi Prices)             (Payment Links + Webhooks)
```

---

## 🔑 Key Differentiators

### 1. Verification Over Generation
The LLM **never does math**. All revenue, transport costs, wastage, and net profit are computed in Python using `Decimal` precision. The LLM only explains pre-computed results in farmer-friendly Tamil/English.

```python
# core/profit_calculator.py — deterministic, unit-tested
def calculate_net_profit(revenue: Decimal, transport_cost: Decimal, wastage_cost: Decimal) -> Decimal:
    return revenue - transport_cost - wastage_cost
```

### 2. Real Agentic Behavior
Not a single prompt→response. A 5-step state machine with:
- **Tool calling:** Each step invokes a specific tool with defined inputs/outputs
- **Retry logic:** Up to 2 retries on transient API failures
- **Graceful degradation:** API down → cached data; unknown crop → ask user; transport full → recommend local
- **Full audit trail:** Every tool call logged with inputs, outputs, timing, and status

### 3. Measured Outcomes
Backtested across **55 synthetic scenarios** covering:
- 20 standard crop/market combinations
- 8 high-quantity scenarios (transport capacity constraints)
- 8 perishable goods (wastage matters)
- 19 edge cases (unknown crops, no transport, ambiguous queries, API failures)

### 4. Payments Integration
Razorpay payment links enable **digital settlement** for farmer→buyer transactions:
- Generate payment link after recommendation
- Track payment status (created → paid → settled)
- Settlement dashboard showing ₹ collected vs pending
- Webhook handling for real-time payment confirmation

---

## 🛠️ Tech Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Frontend | Streamlit | Rapid prototyping, bilingual support, chart integration |
| AI/LLM | Google Gemini 2.5 Flash | Fast, cost-effective, good Tamil language support |
| Data Models | Pydantic v2 | Type safety, validation, serialization |
| Math | Python `Decimal` | Exact arithmetic for financial calculations |
| Live Data | data.gov.in API | Official government mandi price data |
| Payments | Razorpay Python SDK | Test-mode payment links + webhooks |
| Charts | Plotly | Interactive profit comparison visualizations |
| Testing | Pytest | Unit + integration tests with mocks |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- API Keys (see below)

### 1. Clone & Install
```bash
git clone https://github.com/Karthikadivi/uzhavan-unavu.git
cd uzhavan-unavu
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
cp .env.example .env
# Edit .env with your keys:
```

| Key | Required | How to Get |
|-----|----------|-----------|
| `GOOGLE_API_KEY` | ✅ Yes | [Google AI Studio](https://aistudio.google.com/apikey) |
| `DATA_GOV_API_KEY` | ✅ Yes | [data.gov.in](https://data.gov.in) → Register → API Key |
| `RAZORPAY_KEY_ID` | Optional | [Razorpay Dashboard](https://dashboard.razorpay.com) → Test Mode → API Keys |
| `RAZORPAY_KEY_SECRET` | Optional | Same as above |

### 3. Run
```bash
streamlit run app.py
```

### 4. Run Tests
```bash
pytest tests/ -v
```

### 5. Run Evaluation
```bash
python -m evaluation.backtest --output evaluation/results/
```

---

## 📁 Project Structure

```
uzhavan-unavu/
├── app.py                          # Streamlit frontend (bilingual, 5-tab dashboard)
├── agent/
│   ├── orchestrator.py             # Agent state machine with retry + audit
│   ├── tools.py                    # 5 tool definitions
│   └── prompts.py                  # Constrained system prompts
├── core/
│   ├── models.py                   # Pydantic data models
│   ├── price_engine.py             # Live mandi price fetching + caching
│   ├── profit_calculator.py        # Deterministic Decimal math
│   └── transport_checker.py        # Logistics feasibility engine
├── payments/
│   ├── razorpay_client.py          # Payment link generation
│   ├── webhook_handler.py          # Payment confirmation webhooks
│   └── settlement_tracker.py       # ₹ collected/pending tracking
├── data/
│   ├── markets_config.json         # 25+ TN market metadata
│   ├── transport_routes.json       # 30 transport routes
│   └── synthetic_batch.json        # 55 test scenarios
├── evaluation/
│   ├── backtest.py                 # Batch evaluation runner
│   └── metrics.py                  # Accuracy, uplift, latency metrics
├── tests/
│   ├── test_profit_calculator.py   # 15+ unit tests
│   ├── test_transport_checker.py   # 12+ unit tests
│   ├── test_agent_orchestrator.py  # 8+ integration tests
│   └── test_payment_flow.py        # 9+ payment tests
├── requirements.txt
├── ARCHITECTURE.md
├── .env.example
└── .gitignore
```

---

## 📊 Evaluation Results

| Metric | Target | Description |
|--------|--------|-------------|
| Recommendation Accuracy | ≥ 85% | % of times agent picked the optimal market |
| Avg Profit Uplift | ≥ ₹15/kg | Additional income vs. selling locally |
| Failure Handling Rate | 100% | Edge cases handled gracefully (no crash) |
| Response Latency P95 | < 8s | End-to-end recommendation time |
| Unit Test Coverage | ≥ 90% | Coverage on core/ computation engine |

Run `python -m evaluation.backtest` to generate fresh metrics with your API keys.

---

## 🛡️ Failure Handling Matrix

| Scenario | Agent Response |
|----------|---------------|
| data.gov.in API down | Falls back to cached prices + shows warning |
| Unknown/misspelled crop | Asks user to clarify — never hallucinates |
| Transport capacity exceeded | Recommends local sale + explains why |
| Razorpay not configured | Payment tab disabled, rest works normally |
| Ambiguous query (no quantity) | Parses what it can, asks for missing info |
| All markets same price | Recommends local to save transport costs |

---

## 🏗️ Design Decisions

1. **Why Decimal, not float?** Financial calculations need exact arithmetic. `0.1 + 0.2 ≠ 0.3` in float. We use `Decimal` everywhere money is involved.

2. **Why constrain the LLM?** LLMs hallucinate numbers. Our system prompt explicitly says "never perform arithmetic." The LLM receives a pre-computed profit table and only generates natural language explanations.

3. **Why Razorpay integration?** This is a Razorpay buildathon. Even in the Open track, showing payments-domain competence (payment links, webhooks, settlement tracking) signals direct relevance.

4. **Why 55 test scenarios, not 5?** The buildathon specifically says "a held-out test set / 50+ record batch — not one cherry-picked example." We built exactly what they asked for.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

**Karthikadivi** — [GitHub](https://github.com/Karthikadivi)

Built with ❤️ for Tamil Nadu farmers and the Razorpay AI Buildathon 2026.
