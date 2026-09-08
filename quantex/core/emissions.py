"""
Environmental and Economic Sustainability Engine.
Calculates fuel consumption, greenhouse gas (CO2) emissions, and monetary savings.
"""

from typing import Dict, List, Optional
from quantex.core.problem_model import Vehicle, RoutingProblem


class GreenLogisticsEngine:
    """
    Computes environmental impact and efficiency metrics for vehicle routes.
    Standards:
    - Average Diesel Van: ~0.10 L/km (185g CO2/km)
    - Average Gas Delivery Truck: ~0.15 L/km (260g CO2/km)
    - Electric Delivery Van: ~0.25 kWh/km (0 direct tailpipe CO2, ~45g grid CO2/km)
    - Cargo Bike / Drone: 0g CO2/km
    - Fuel cost benchmark: $1.40 / L (or equivalent local rate)
    - Electricity cost benchmark: $0.15 / kWh
    - Carbon offset price: $40.00 / metric ton CO2
    """

    FUEL_CONSUMPTION_RATES = {
        "Diesel_Van": 0.10,      # L / km
        "Gas_Truck": 0.15,       # L / km
        "Electric_Van": 0.25,    # kWh / km
        "Cargo_Bike": 0.0        # None
    }

    EMISSION_FACTORS = {
        "Diesel_Van": 185.0,     # g CO2 / km
        "Gas_Truck": 260.0,      # g CO2 / km
        "Electric_Van": 45.0,    # g CO2 / km (life-cycle electricity mix)
        "Cargo_Bike": 0.0
    }

    FUEL_COST_PER_UNIT = {
        "Diesel_Van": 1.40,      # USD per Liter
        "Gas_Truck": 1.35,       # USD per Liter
        "Electric_Van": 0.15,    # USD per kWh
        "Cargo_Bike": 0.0
    }

    @classmethod
    def evaluate_route_sustainability(
        cls,
        route: List[int],
        problem: RoutingProblem,
        vehicle: Vehicle
    ) -> Dict[str, float]:
        """
        Calculates distance, time, fuel, emissions, and cost for a single vehicle route.
        """
        if len(route) < 2:
            return {
                "distance_km": 0.0,
                "travel_time_min": 0.0,
                "service_time_min": 0.0,
                "total_time_min": 0.0,
                "fuel_consumed": 0.0,
                "fuel_unit": "L",
                "co2_emissions_kg": 0.0,
                "fuel_cost": 0.0,
                "labor_cost": 0.0,
                "total_operational_cost": 0.0
            }

        dist_matrix = problem.effective_distance_matrix
        total_distance = 0.0
        service_time = 0.0

        for idx in range(len(route) - 1):
            u, v = route[idx], route[idx + 1]
            total_distance += dist_matrix[u][v]
            if not problem.nodes[u].is_depot:
                service_time += problem.nodes[u].service_duration

        # Also add last stop service time if not depot
        last_node = route[-1]
        if not problem.nodes[last_node].is_depot and len(route) > 2:
            service_time += problem.nodes[last_node].service_duration

        travel_time_min = (total_distance / max(1.0, vehicle.avg_speed_kmh)) * 60.0
        total_time_min = travel_time_min + service_time

        v_type = vehicle.vehicle_type if vehicle.vehicle_type in cls.FUEL_CONSUMPTION_RATES else "Diesel_Van"
        fuel_rate = cls.FUEL_CONSUMPTION_RATES.get(v_type, 0.10)
        emission_rate = vehicle.emission_factor_g_km if vehicle.emission_factor_g_km > 0 else cls.EMISSION_FACTORS.get(v_type, 185.0)
        fuel_cost_rate = cls.FUEL_COST_PER_UNIT.get(v_type, 1.40)
        fuel_unit = "kWh" if v_type == "Electric_Van" else "L"

        fuel_consumed = total_distance * fuel_rate
        co2_emissions_kg = (total_distance * emission_rate) / 1000.0
        fuel_cost = fuel_consumed * fuel_cost_rate
        labor_cost = (total_time_min / 60.0) * vehicle.cost_per_hour
        total_cost = (total_distance * vehicle.cost_per_km) + fuel_cost + labor_cost

        return {
            "distance_km": round(total_distance, 2),
            "travel_time_min": round(travel_time_min, 1),
            "service_time_min": round(service_time, 1),
            "total_time_min": round(total_time_min, 1),
            "fuel_consumed": round(fuel_consumed, 2),
            "fuel_unit": fuel_unit,
            "co2_emissions_kg": round(co2_emissions_kg, 2),
            "fuel_cost": round(fuel_cost, 2),
            "labor_cost": round(labor_cost, 2),
            "total_operational_cost": round(total_cost, 2)
        }

    @classmethod
    def compare_solutions(
        cls,
        quantum_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compares optimized quantum route metrics against a baseline (e.g., naive or greedy classical).
        """
        def pct_saving(base: float, opt: float) -> float:
            if base <= 0:
                return 0.0
            return round(((base - opt) / base) * 100.0, 2)

        dist_saved = max(0.0, baseline_metrics.get("distance_km", 0) - quantum_metrics.get("distance_km", 0))
        fuel_saved = max(0.0, baseline_metrics.get("fuel_consumed", 0) - quantum_metrics.get("fuel_consumed", 0))
        co2_saved = max(0.0, baseline_metrics.get("co2_emissions_kg", 0) - quantum_metrics.get("co2_emissions_kg", 0))
        time_saved = max(0.0, baseline_metrics.get("total_time_min", 0) - quantum_metrics.get("total_time_min", 0))
        cost_saved = max(0.0, baseline_metrics.get("total_operational_cost", 0) - quantum_metrics.get("total_operational_cost", 0))

        return {
            "distance_saved_km": round(dist_saved, 2),
            "distance_pct_saved": pct_saving(baseline_metrics.get("distance_km", 0), quantum_metrics.get("distance_km", 0)),
            "fuel_saved": round(fuel_saved, 2),
            "fuel_pct_saved": pct_saving(baseline_metrics.get("fuel_consumed", 0), quantum_metrics.get("fuel_consumed", 0)),
            "co2_saved_kg": round(co2_saved, 2),
            "co2_pct_saved": pct_saving(baseline_metrics.get("co2_emissions_kg", 0), quantum_metrics.get("co2_emissions_kg", 0)),
            "time_saved_min": round(time_saved, 1),
            "time_pct_saved": pct_saving(baseline_metrics.get("total_time_min", 0), quantum_metrics.get("total_time_min", 0)),
            "cost_saved_usd": round(cost_saved, 2),
            "cost_pct_saved": pct_saving(baseline_metrics.get("total_operational_cost", 0), quantum_metrics.get("total_operational_cost", 0))
        }
