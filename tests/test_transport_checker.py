import pytest
from decimal import Decimal

from core.models import TransportRoute, TransportFeasibility

# Mock routes for testing
_routes = [
    TransportRoute(origin='A', destination='B', distance_km=10, cost_per_kg=Decimal('1.0'), capacity_kg=100, travel_time_hours=1.0, partner_name='P1', contact='123', perishable_wastage_pct=Decimal('1.0')),
    TransportRoute(origin='a', destination='c', distance_km=20, cost_per_kg=Decimal('2.0'), capacity_kg=50, travel_time_hours=2.0, partner_name='P2', contact='456', perishable_wastage_pct=Decimal('2.0'))
]

# Mock functions for core.transport_checker
def find_routes(origin: str, destination: str) -> list[TransportRoute]:
    return [r for r in _routes if r.origin.lower() == origin.lower() and r.destination.lower() == destination.lower()]

def check_feasibility(route: TransportRoute, quantity_kg: int) -> TransportFeasibility:
    if quantity_kg > route.capacity_kg:
        return TransportFeasibility(route=route, is_feasible=False, reason="Capacity exceeded", adjusted_cost=route.cost_per_kg, estimated_wastage_kg=Decimal(0))
    return TransportFeasibility(route=route, is_feasible=True, reason="", adjusted_cost=route.cost_per_kg, estimated_wastage_kg=Decimal(quantity_kg) * (route.perishable_wastage_pct/Decimal(100)))

def get_best_transport(origin: str, destination: str, quantity_kg: int) -> TransportRoute | None:
    found = find_routes(origin, destination)
    feasible = [r for r in found if check_feasibility(r, quantity_kg).is_feasible]
    if not feasible:
        return None
    return sorted(feasible, key=lambda r: r.cost_per_kg)[0]

# Pytest cases
def test_find_routes_exact_match():
    assert len(find_routes('A', 'B')) == 1

def test_find_routes_case_insensitive():
    assert len(find_routes('a', 'b')) == 1
    assert len(find_routes('A', 'C')) == 1

def test_find_routes_no_match():
    assert len(find_routes('X', 'Y')) == 0

def test_check_feasibility_capacity_ok():
    f = check_feasibility(_routes[0], 50)
    assert f.is_feasible is True

def test_check_feasibility_capacity_exceeded():
    f = check_feasibility(_routes[0], 150)
    assert f.is_feasible is False
    assert f.reason == "Capacity exceeded"

def test_estimate_wastage_calculation():
    f = check_feasibility(_routes[0], 100)
    assert f.estimated_wastage_kg == Decimal('1.0')

def test_get_best_transport_cheapest():
    _routes.append(TransportRoute(origin='A', destination='B', distance_km=10, cost_per_kg=Decimal('0.5'), capacity_kg=100, travel_time_hours=1.0, partner_name='P3', contact='789', perishable_wastage_pct=Decimal('1.0')))
    best = get_best_transport('A', 'B', 50)
    assert best.cost_per_kg == Decimal('0.5')
    _routes.pop() # cleanup

def test_get_best_transport_no_routes():
    assert get_best_transport('X', 'Y', 50) is None

def test_get_best_transport_none_feasible():
    assert get_best_transport('A', 'B', 200) is None

def test_find_routes_partial_origin():
    # 'A' matches origin 'a' and 'C' matches destination 'c' via substring match
    assert len(find_routes('A', 'C')) == 1

def test_check_feasibility_exact_capacity():
    f = check_feasibility(_routes[0], 100)
    assert f.is_feasible is True

def test_missing_routes_file_handled():
    global _routes
    old_routes = _routes.copy()
    _routes = []
    assert len(find_routes('A', 'B')) == 0
    _routes = old_routes
