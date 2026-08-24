import json
import logging
import os
from decimal import Decimal

from core.models import TransportFeasibility, TransportRoute

logger = logging.getLogger(__name__)


class TransportChecker:
    def __init__(self, routes_file: str = 'data/transport_routes.json'):
        self.routes_file = routes_file
        self.routes: list[TransportRoute] = []
        self._load_routes()

    def _load_routes(self) -> None:
        if not os.path.exists(self.routes_file):
            logger.warning(f"Routes file {self.routes_file} not found.")
            return

        try:
            with open(self.routes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                routes_list = data.get('routes', data) if isinstance(data, dict) else data
                for item in routes_list:
                    item['cost_per_kg'] = Decimal(str(item.get('cost_per_kg', 0)))
                    item['perishable_wastage_pct'] = Decimal(str(item.get('perishable_wastage_pct', 0)))
                    self.routes.append(TransportRoute(**item))
        except Exception as e:
            logger.error(f"Error loading routes: {e}")

    def find_routes(self, origin: str, destination: str) -> list[TransportRoute]:
        matched_routes = []
        origin_lower = origin.lower()
        destination_lower = destination.lower()
        for route in self.routes:
            if origin_lower in route.origin.lower() and destination_lower in route.destination.lower():
                matched_routes.append(route)
        return matched_routes

    def estimate_wastage(self, route: TransportRoute, quantity_kg: Decimal) -> Decimal:
        return quantity_kg * (route.perishable_wastage_pct / Decimal('100'))

    def check_feasibility(self, route: TransportRoute, quantity_kg: Decimal, is_perishable: bool = True) -> TransportFeasibility:
        if quantity_kg > route.capacity_kg:
            return TransportFeasibility(
                route=route,
                is_feasible=False,
                reason=f"Quantity {quantity_kg}kg exceeds route capacity {route.capacity_kg}kg",
                adjusted_cost=Decimal('0'),
                estimated_wastage_kg=Decimal('0')
            )

        wastage_kg = Decimal('0')
        if is_perishable:
            wastage_kg = self.estimate_wastage(route, quantity_kg)

        adjusted_cost = route.cost_per_kg * quantity_kg

        return TransportFeasibility(
            route=route,
            is_feasible=True,
            reason="Route is feasible",
            adjusted_cost=adjusted_cost,
            estimated_wastage_kg=wastage_kg
        )

    def get_best_transport(self, origin: str, destination: str, quantity_kg: Decimal, is_perishable: bool = True) -> TransportFeasibility | None:
        routes = self.find_routes(origin, destination)
        if not routes:
            return None

        feasible_options = []
        for route in routes:
            feasibility = self.check_feasibility(route, quantity_kg, is_perishable)
            if feasibility.is_feasible:
                feasible_options.append(feasibility)

        if not feasible_options:
            return None

        # Sort by adjusted_cost to find the cheapest feasible option
        return sorted(feasible_options, key=lambda f: f.adjusted_cost)[0]
