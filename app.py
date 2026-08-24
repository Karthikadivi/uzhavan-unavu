"""
🌾 Uzhavan Unavu — Farmer's Market Intelligence Agent
Built for Razorpay AI Buildathon 2026

A production-grade agentic AI system that helps Tamil Nadu farmers
find the best market prices, with deterministic computation,
live data, and Razorpay payment integration.
"""

import os
import sys
import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="🌾 Uzhavan Unavu — Farmer's Market Agent",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B5E20;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #1B5E20;
    }
    .audit-entry {
        font-family: monospace;
        font-size: 0.85rem;
        padding: 0.3rem 0;
        border-bottom: 1px solid #eee;
    }
    .status-ok { color: #2E7D32; font-weight: bold; }
    .status-fail { color: #C62828; font-weight: bold; }
    .status-warn { color: #F57F17; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
def get_api_key(key_name: str, streamlit_key: str | None = None) -> str | None:
    """Get API key from environment or Streamlit secrets."""
    # Try env var first
    value = os.environ.get(key_name)
    if value:
        return value
    # Try Streamlit secrets
    try:
        if streamlit_key:
            return st.secrets.get(streamlit_key, None)
        return st.secrets.get(key_name, None)
    except Exception:
        return None


def check_api_status() -> dict:
    """Check which APIs are available."""
    status = {
        "gemini": bool(get_api_key("GOOGLE_API_KEY")),
        "data_gov": bool(get_api_key("DATA_GOV_API_KEY")),
        "razorpay": bool(get_api_key("RAZORPAY_KEY_ID")),
    }
    return status


def format_inr(amount: Decimal | float) -> str:
    """Format a number as Indian Rupees."""
    if isinstance(amount, float):
        amount = Decimal(str(amount))
    return f"₹{amount:,.2f}"


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# --- Sidebar ---
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    # Language toggle
    language = st.radio(
        "🌐 Language / மொழி",
        ["English", "தமிழ் (Tamil)"],
        index=0,
        help="Select your preferred language"
    )
    is_tamil = language == "தமிழ் (Tamil)"

    st.divider()

    # API Status Indicators
    st.markdown("### 📡 API Status")
    api_status = check_api_status()

    col1, col2 = st.columns(2)
    with col1:
        if api_status["gemini"]:
            st.markdown("✅ Gemini AI")
        else:
            st.markdown("❌ Gemini AI")

        if api_status["data_gov"]:
            st.markdown("✅ Market Data")
        else:
            st.markdown("⚠️ Market Data")

    with col2:
        if api_status["razorpay"]:
            st.markdown("✅ Razorpay")
        else:
            st.markdown("⚠️ Razorpay")

    if not api_status["gemini"]:
        st.error("⚠️ Gemini API key required. Add GOOGLE_API_KEY to .env")

    st.divider()

    # Commodity quick-reference
    st.markdown("### 🌱 Supported Crops")
    crops = {
        "Jasmine (மல்லி)": "Malli",
        "Tomato (தக்காளி)": "Thakkali",
        "Banana (வாழை)": "Vazhai",
        "Turmeric (மஞ்சள்)": "Manjal",
        "Onion (வெங்காயம்)": "Vengayam",
        "Coconut (தேங்காய்)": "Thengai",
        "Groundnut": "Verkadalai",
        "Paddy/Rice": "Nellu",
        "Drumstick": "Murungai",
        "Tamarind": "Puli",
    }
    for crop, tamil in crops.items():
        st.markdown(f"• {crop}")

    st.divider()
    st.markdown(
        "**Built for [Razorpay AI Buildathon 2026](https://razorpay.com/buildathon)**"
    )
    st.markdown("Made with ❤️ by Karthikadivi")


# --- Main Content ---
st.markdown('<p class="main-header">🌾 Uzhavan Unavu — உழவன் உணவு</p>', unsafe_allow_html=True)
if is_tamil:
    st.markdown(
        '<p class="sub-header">உங்கள் விளைபொருளுக்கு சிறந்த சந்தை விலையை கண்டறியும் AI முகவர்</p>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<p class="sub-header">AI-Powered Market Intelligence Agent for Tamil Nadu Farmers</p>',
        unsafe_allow_html=True
    )

# --- Input Section ---
st.markdown("---")

input_mode = st.radio(
    "📝 Input Mode" if not is_tamil else "📝 உள்ளீட்டு முறை",
    ["Structured Form" if not is_tamil else "படிவம்",
     "Natural Language" if not is_tamil else "இயல்பான மொழி"],
    horizontal=True
)

col_input, col_info = st.columns([2, 1])

with col_input:
    if input_mode in ["Structured Form", "படிவம்"]:
        # Structured form input
        commodity_options = [
            "Jasmine", "Tomato", "Banana", "Turmeric", "Onion",
            "Coconut", "Groundnut", "Paddy", "Drumstick", "Tamarind",
            "Cotton", "Sugarcane", "Curry Leaves", "Mango"
        ]
        commodity = st.selectbox(
            "🌾 Crop / பயிர்" if not is_tamil else "🌾 பயிர்",
            commodity_options
        )

        quantity = st.slider(
            "📦 Quantity (kg)" if not is_tamil else "📦 அளவு (கிலோ)",
            min_value=10, max_value=500, value=50, step=10
        )

        origin_options = [
            "Madurai", "Chennai", "Coimbatore", "Trichy", "Salem",
            "Thanjavur", "Erode", "Tirunelveli", "Dindigul", "Vellore",
            "Pollachi", "Kumbakonam"
        ]
        origin = st.selectbox(
            "📍 Your Location / உங்கள் இடம்" if not is_tamil else "📍 உங்கள் இடம்",
            origin_options
        )

        query = f"I have {quantity}kg of {commodity} in {origin}. Where should I sell for the best price?"
    else:
        # Natural language input
        default_query = (
            "எனக்கு மதுரையில் 50 கிலோ மல்லிகைப்பூ உள்ளது. எங்கே விற்பது நல்லது?"
            if is_tamil else
            "I have 50kg of jasmine in Madurai. Where can I get the best price?"
        )
        query = st.text_area(
            "💬 Your Query" if not is_tamil else "💬 உங்கள் கேள்வி",
            value=default_query,
            height=100
        )
        commodity = None
        quantity = None
        origin = None

with col_info:
    st.markdown("### 🤖 How It Works" if not is_tamil else "### 🤖 இது எப்படி வேலை செய்கிறது")
    st.markdown("""
    1. **Parse** your query → extract crop, quantity, location
    2. **Fetch** live mandi prices from government APIs
    3. **Compute** revenue, transport costs, wastage — all in Python
    4. **Rank** markets by net profit
    5. **Explain** results in simple language
    6. **Pay** via Razorpay payment link (optional)

    *All math is deterministic — the AI only explains, never calculates.*
    """)

# --- Run Agent ---
run_label = "🚀 Get Recommendation" if not is_tamil else "🚀 ஆலோசனை பெறுக"
if st.button(run_label, type="primary", use_container_width=True):

    if not api_status["gemini"]:
        st.error("❌ Please configure your GOOGLE_API_KEY to use this feature.")
        st.stop()

    with st.spinner("🔍 Analyzing markets..." if not is_tamil else "🔍 சந்தைகளை ஆராய்கிறோம்..."):
        try:
            from agent.orchestrator import AgentOrchestrator

            # Initialize orchestrator
            orchestrator = AgentOrchestrator(
                google_api_key=get_api_key("GOOGLE_API_KEY"),
                data_gov_api_key=get_api_key("DATA_GOV_API_KEY"),
                razorpay_key_id=get_api_key("RAZORPAY_KEY_ID"),
                razorpay_key_secret=get_api_key("RAZORPAY_KEY_SECRET"),
            )

            # Run agent
            state = orchestrator.run(query)

            # Store state in session for payment tab
            st.session_state["agent_state"] = state
            st.session_state["orchestrator"] = orchestrator

        except Exception as e:
            st.error(f"❌ Agent error: {str(e)}")
            st.stop()

    # --- Results Tabs ---
    if "agent_state" in st.session_state:
        state = st.session_state["agent_state"]

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Recommendation" if not is_tamil else "📊 பரிந்துரை",
            "📈 Profit Comparison" if not is_tamil else "📈 லாப ஒப்பீடு",
            "📝 Decision Log" if not is_tamil else "📝 முடிவு பதிவு",
            "💳 Payment" if not is_tamil else "💳 கட்டணம்",
            "🧪 Evaluation" if not is_tamil else "🧪 மதிப்பீடு"
        ])

        # --- Tab 1: Recommendation ---
        with tab1:
            if state.recommendation:
                rec = state.recommendation
                best = rec.best_market

                # Key metrics
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric(
                        "🏆 Best Market" if not is_tamil else "🏆 சிறந்த சந்தை",
                        best.market.market_name
                    )
                with col_m2:
                    st.metric(
                        "💰 Net Profit" if not is_tamil else "💰 நிகர லாபம்",
                        format_inr(best.net_profit)
                    )
                with col_m3:
                    st.metric(
                        "📊 Margin" if not is_tamil else "📊 லாப வீதம்",
                        f"{best.profit_margin_pct}%"
                    )
                with col_m4:
                    confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}
                    st.metric(
                        "🎯 Confidence" if not is_tamil else "🎯 நம்பிக்கை",
                        f"{confidence_emoji.get(rec.confidence, '⚪')} {rec.confidence.title()}"
                    )

                # Warnings
                if rec.warnings:
                    for w in rec.warnings:
                        st.warning(f"⚠️ {w}")

                st.divider()

                # AI Explanation
                st.markdown("### 💬 AI Explanation" if not is_tamil else "### 💬 AI விளக்கம்")
                st.markdown(rec.explanation)

                # Profit comparison table
                st.markdown("### 📋 Market Comparison" if not is_tamil else "### 📋 சந்தை ஒப்பீடு")
                table_data = []
                for analysis in rec.all_analyses:
                    table_data.append({
                        "Market": analysis.market.market_name,
                        "Price/kg": format_inr(analysis.market.modal_price / Decimal("100")),
                        "Revenue": format_inr(analysis.revenue),
                        "Transport": format_inr(analysis.transport_cost),
                        "Wastage": format_inr(analysis.wastage_cost),
                        "Net Profit": format_inr(analysis.net_profit),
                        "Margin %": f"{analysis.profit_margin_pct}%",
                        "Local?": "✅ Yes" if analysis.is_local else "❌ No"
                    })
                st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

            elif state.errors:
                for err in state.errors:
                    st.error(f"❌ {err}")
            else:
                st.info("No recommendation generated. Please try a different query.")

        # --- Tab 2: Profit Comparison Chart ---
        with tab2:
            if state.recommendation and state.recommendation.all_analyses:
                analyses = state.recommendation.all_analyses

                # Bar chart - Net Profit by Market
                fig = go.Figure()
                market_names = [a.market.market_name for a in analyses]
                net_profits = [float(a.net_profit) for a in analyses]
                colors = ['#1B5E20' if a == state.recommendation.best_market else '#81C784'
                          for a in analyses]

                fig.add_trace(go.Bar(
                    x=market_names,
                    y=net_profits,
                    marker_color=colors,
                    text=[format_inr(Decimal(str(p))) for p in net_profits],
                    textposition='outside'
                ))
                fig.update_layout(
                    title="Net Profit by Market (₹)" if not is_tamil else "சந்தை வாரியாக நிகர லாபம் (₹)",
                    xaxis_title="Market",
                    yaxis_title="Net Profit (₹)",
                    showlegend=False,
                    height=450
                )
                st.plotly_chart(fig, use_container_width=True)

                # Breakdown stacked bar
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    name='Revenue',
                    x=market_names,
                    y=[float(a.revenue) for a in analyses],
                    marker_color='#4CAF50'
                ))
                fig2.add_trace(go.Bar(
                    name='Transport Cost',
                    x=market_names,
                    y=[-float(a.transport_cost) for a in analyses],
                    marker_color='#FF9800'
                ))
                fig2.add_trace(go.Bar(
                    name='Wastage Cost',
                    x=market_names,
                    y=[-float(a.wastage_cost) for a in analyses],
                    marker_color='#F44336'
                ))
                fig2.update_layout(
                    title="Cost Breakdown by Market" if not is_tamil else "சந்தை வாரியான செலவு பிரிப்பு",
                    barmode='relative',
                    xaxis_title="Market",
                    yaxis_title="Amount (₹)",
                    height=450
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Run a query to see profit comparisons.")

        # --- Tab 3: Decision Log (Audit Trail) ---
        with tab3:
            st.markdown("### 📝 Agent Decision Log" if not is_tamil else "### 📝 முகவர் முடிவு பதிவு")
            st.markdown("*Every tool call is logged with inputs, outputs, and timing.*")

            if state.audit_log:
                for i, entry in enumerate(state.audit_log):
                    status_class = {
                        "success": "status-ok",
                        "failure": "status-fail",
                        "fallback": "status-warn"
                    }.get(entry.status, "")

                    status_emoji = {
                        "success": "✅",
                        "failure": "❌",
                        "fallback": "⚠️"
                    }.get(entry.status, "❓")

                    with st.expander(
                        f"{status_emoji} Step {i+1}: {entry.step} → {entry.tool_name} "
                        f"({entry.duration_ms}ms) [{entry.status.upper()}]"
                    ):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown("**Inputs:**")
                            st.json(json.loads(json.dumps(entry.inputs, default=decimal_to_float)))
                        with col_b:
                            st.markdown("**Outputs:**")
                            # Truncate large outputs for display
                            outputs_str = json.dumps(entry.outputs, default=decimal_to_float)
                            if len(outputs_str) > 2000:
                                st.json(json.loads(outputs_str[:2000] + '..."'))
                            else:
                                st.json(json.loads(outputs_str))
                        st.caption(f"Timestamp: {entry.timestamp.isoformat()}")

                # Summary stats
                st.divider()
                total_time = sum(e.duration_ms for e in state.audit_log)
                successes = sum(1 for e in state.audit_log if e.status == "success")
                failures = sum(1 for e in state.audit_log if e.status == "failure")
                fallbacks = sum(1 for e in state.audit_log if e.status == "fallback")

                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                col_s1.metric("Total Steps", len(state.audit_log))
                col_s2.metric("Total Time", f"{total_time}ms")
                col_s3.metric("Successes", f"{successes} ✅")
                col_s4.metric("Fallbacks", f"{fallbacks} ⚠️" if fallbacks else f"{failures} ❌")
            else:
                st.info("No audit log entries yet. Run a query to see the decision trail.")

        # --- Tab 4: Payment ---
        with tab4:
            st.markdown("### 💳 Razorpay Payment Link" if not is_tamil else "### 💳 ரேசர்பே கட்டண இணைப்பு")
            st.markdown(
                "*Generate a payment link to send to the buyer for advance/guaranteed payment "
                "before shipping your produce.*"
            )

            if not api_status["razorpay"]:
                st.warning(
                    "⚠️ Razorpay is not configured. Add RAZORPAY_KEY_ID and "
                    "RAZORPAY_KEY_SECRET to your .env file to enable payments."
                )
                st.markdown("""
                **To set up Razorpay (Test Mode):**
                1. Create an account at [razorpay.com](https://razorpay.com)
                2. Go to Account & Settings → API Keys
                3. Generate Test Mode keys (`rzp_test_...`)
                4. Add them to your `.env` file
                """)
            else:
                if state.recommendation:
                    best = state.recommendation.best_market
                    st.success(
                        f"Recommended sale: {format_inr(best.net_profit)} at "
                        f"{best.market.market_name}"
                    )

                    with st.form("payment_form"):
                        st.markdown("**Buyer Details:**")
                        buyer_name = st.text_input("Buyer Name", "Test Buyer")
                        buyer_contact = st.text_input("Buyer Phone", "+919999999999")
                        buyer_email = st.text_input("Buyer Email", "buyer@example.com")

                        payment_amount = st.number_input(
                            "Payment Amount (₹)",
                            min_value=1.0,
                            value=float(best.net_profit),
                            step=100.0
                        )

                        submitted = st.form_submit_button(
                            "🔗 Generate Payment Link",
                            type="primary"
                        )

                        if submitted:
                            try:
                                orchestrator = st.session_state.get("orchestrator")
                                if orchestrator:
                                    updated_state = orchestrator.generate_payment_link(
                                        state=state,
                                        buyer_name=buyer_name,
                                        buyer_contact=buyer_contact,
                                        buyer_email=buyer_email
                                    )
                                    st.session_state["agent_state"] = updated_state
                                    if updated_state.payment_link:
                                        st.success(f"✅ Payment link generated!")
                                        st.markdown(f"**Payment Link:** [{updated_state.payment_link}]({updated_state.payment_link})")
                                        st.balloons()
                                    else:
                                        st.error("Failed to generate payment link.")
                                else:
                                    st.error("Agent not initialized.")
                            except Exception as e:
                                st.error(f"Payment error: {str(e)}")

                    # Settlement tracker summary
                    st.divider()
                    st.markdown("### 📊 Settlement Dashboard")
                    try:
                        from payments.settlement_tracker import SettlementTracker
                        tracker = SettlementTracker()
                        summary = tracker.get_summary()

                        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                        col_p1.metric("Total Links", summary.get("total_created", 0))
                        col_p2.metric("Paid ✅", summary.get("total_paid", 0))
                        col_p3.metric("Pending ⏳", summary.get("total_pending", 0))
                        col_p4.metric(
                            "₹ Collected",
                            format_inr(summary.get("amount_collected", Decimal("0")))
                        )
                    except Exception:
                        st.info("No payment history yet.")
                else:
                    st.info("Run a query first to get a recommendation, then generate a payment link.")

        # --- Tab 5: Evaluation ---
        with tab5:
            st.markdown("### 🧪 Batch Evaluation" if not is_tamil else "### 🧪 தொகுதி மதிப்பீடு")
            st.markdown(
                "*Run the agent across 50+ synthetic scenarios to measure accuracy, "
                "profit uplift, and failure handling.*"
            )

            # Check if evaluation results exist
            results_path = os.path.join("evaluation", "results", "report.md")
            if os.path.exists(results_path):
                st.markdown("#### 📋 Latest Evaluation Report")
                with open(results_path, "r") as f:
                    st.markdown(f.read())

                # Load and display results
                results_json_path = os.path.join("evaluation", "results", "results.json")
                if os.path.exists(results_json_path):
                    with open(results_json_path, "r") as f:
                        results = json.load(f)

                    # Accuracy by category chart
                    categories = {}
                    for r in results:
                        cat = r.get("category", "unknown")
                        if cat not in categories:
                            categories[cat] = {"total": 0, "correct": 0}
                        categories[cat]["total"] += 1
                        if r.get("handled_gracefully", False):
                            categories[cat]["correct"] += 1

                    if categories:
                        fig_cat = go.Figure(go.Bar(
                            x=list(categories.keys()),
                            y=[c["correct"]/c["total"]*100 for c in categories.values()],
                            marker_color='#1B5E20',
                            text=[f"{c['correct']}/{c['total']}" for c in categories.values()],
                            textposition='outside'
                        ))
                        fig_cat.update_layout(
                            title="Success Rate by Category (%)",
                            yaxis_title="Success %",
                            height=400
                        )
                        st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info(
                    "No evaluation results found. Run the backtest to generate metrics:"
                )
                st.code("python -m evaluation.backtest --output evaluation/results/", language="bash")

                if st.button("🚀 Run Backtest Now", type="secondary"):
                    st.warning(
                        "⚠️ This will run 50+ scenarios and may take several minutes. "
                        "It requires a valid GOOGLE_API_KEY."
                    )
                    st.info("Run from terminal for best results: `python -m evaluation.backtest`")


# --- Footer ---
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.markdown("🌾 **Uzhavan Unavu v2.0**")
    st.markdown("Built for Razorpay AI Buildathon 2026")
with col_f2:
    st.markdown("📊 **Architecture**")
    st.markdown("[View Architecture Docs](ARCHITECTURE.md)")
with col_f3:
    st.markdown("💻 **Source Code**")
    st.markdown("[GitHub Repository](https://github.com/Karthikadivi/uzhavan-unavu)")