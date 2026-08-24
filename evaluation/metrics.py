import plotly.express as px
import plotly.graph_objects as go
from decimal import Decimal
import os
import statistics
from collections import defaultdict

def recommendation_accuracy(results: list[dict]) -> float:
    """What % of scenarios did the agent pick the expected best market?
    Each result dict has 'expected_best_market' and 'actual_best_market' keys.
    Returns percentage 0-100."""
    if not results:
        return 0.0
    correct = sum(1 for r in results if r.get('expected_best_market') == r.get('actual_best_market'))
    return (correct / len(results)) * 100

def average_profit_uplift(results: list[dict]) -> Decimal:
    """Average additional profit (in INR) from agent recommendation vs local sale.
    Each result has 'recommended_profit' and 'local_profit' Decimal values."""
    if not results:
        return Decimal("0.0")
    uplifts = [Decimal(str(r.get('recommended_profit', 0))) - Decimal(str(r.get('local_profit', 0))) for r in results]
    return sum(uplifts) / Decimal(str(len(uplifts)))

def failure_handling_rate(results: list[dict]) -> float:
    """% of edge-case scenarios handled gracefully (no crash, meaningful message).
    Each result has 'category' and 'handled_gracefully' (bool) keys."""
    edge_cases = [r for r in results if r.get('category') == 'edge_case']
    if not edge_cases:
        return 100.0
    handled = sum(1 for r in edge_cases if r.get('handled_gracefully'))
    return (handled / len(edge_cases)) * 100

def latency_percentiles(results: list[dict]) -> dict:
    """Compute P50, P90, P95 latency from 'latency_ms' field."""
    latencies = [r.get('latency_ms', 0) for r in results if 'latency_ms' in r]
    if not latencies:
        return {'p50': 0.0, 'p90': 0.0, 'p95': 0.0}
    latencies.sort()
    
    def percentile(data, p):
        k = (len(data) - 1) * p
        f = int(k)
        c = int(k) + 1 if k > int(k) else int(k)
        if f == c:
            return float(data[f])
        return float(data[f] * (c - k) + data[c] * (k - f))
        
    return {
        'p50': percentile(latencies, 0.50),
        'p90': percentile(latencies, 0.90),
        'p95': percentile(latencies, 0.95)
    }

def generate_report(results: list[dict], output_dir: str = 'evaluation/results') -> str:
    """Generate a markdown report with all metrics + save charts as PNGs using plotly.
    Charts: profit uplift distribution, accuracy by category, latency histogram.
    Returns the markdown report string."""
    os.makedirs(output_dir, exist_ok=True)
    
    accuracy = recommendation_accuracy(results)
    avg_uplift = average_profit_uplift(results)
    handling_rate = failure_handling_rate(results)
    latencies = latency_percentiles(results)
    
    # 1. Profit Uplift Distribution Chart
    uplifts = [float(Decimal(str(r.get('recommended_profit', 0))) - Decimal(str(r.get('local_profit', 0)))) for r in results]
    if uplifts:
        fig1 = px.histogram(x=uplifts, labels={'x': 'Profit Uplift (INR)', 'y': 'Count'}, title='Profit Uplift Distribution')
        fig1.write_image(os.path.join(output_dir, 'profit_uplift.png'))
    
    # 2. Accuracy by Category Chart
    category_acc = defaultdict(list)
    for r in results:
        cat = r.get('category', 'unknown')
        correct = 1 if r.get('expected_best_market') == r.get('actual_best_market') else 0
        category_acc[cat].append(correct)
        
    if category_acc:
        cats = list(category_acc.keys())
        accs = [(sum(category_acc[c]) / len(category_acc[c])) * 100 for c in cats]
        fig2 = px.bar(x=cats, y=accs, labels={'x': 'Category', 'y': 'Accuracy (%)'}, title='Accuracy by Category')
        fig2.write_image(os.path.join(output_dir, 'accuracy_by_category.png'))
        
    # 3. Latency Histogram
    lats = [r.get('latency_ms', 0) for r in results if 'latency_ms' in r]
    if lats:
        fig3 = px.histogram(x=lats, labels={'x': 'Latency (ms)', 'y': 'Count'}, title='Latency Distribution')
        fig3.write_image(os.path.join(output_dir, 'latency_histogram.png'))
        
    report = f'''# Uzhavan Unavu Backtest Evaluation Report
    
## Core Metrics
- **Recommendation Accuracy**: {accuracy:.2f}%
- **Average Profit Uplift**: ₹{avg_uplift:.2f}
- **Edge-case Graceful Handling**: {handling_rate:.2f}%

## Latency
- **P50**: {latencies["p50"]:.2f} ms
- **P90**: {latencies["p90"]:.2f} ms
- **P95**: {latencies["p95"]:.2f} ms

## Charts
- ![Profit Uplift Distribution](profit_uplift.png)
- ![Accuracy by Category](accuracy_by_category.png)
- ![Latency Distribution](latency_histogram.png)
'''
    with open(os.path.join(output_dir, 'report.md'), 'w', encoding='utf-8') as f:
        f.write(report)
        
    return report
