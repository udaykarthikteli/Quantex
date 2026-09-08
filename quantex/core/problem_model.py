"""
Data models and graph representations for Vehicle Routing Problems (VRP/CVRP/VRPTW).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np


@dataclass
class DeliveryNode:
    """Represents a physical delivery or pickup waypoint."""
    id: int
    name: str
    lat: float
    lon: float
    demand: float = 1.0          # Package weight / cargo units
    time_window_start: float = 0.0  # e.g., in minutes from shift start (0 = 08:00 AM)
    time_window_end: float = 480.0  # 480 = 8 hours
    service_duration: float = 10.0 # Time to deliver in minutes
    priority: int = 1              # 1 (Normal) to 5 (Urgent)
    is_depot: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "demand": self.demand,
            "tw_start": self.time_window_start,
            "tw_end": self.time_window_end,
            "service_time": self.service_duration,
            "priority": self.priority,
            "is_depot": self.is_depot
        }


@dataclass
class Vehicle:
    """Represents a delivery vehicle in the fleet."""
    id: int
    name: str
    capacity: float = 100.0        # Max load capacity
    vehicle_type: str = "Diesel_Van"  # 'Electric_Van', 'Diesel_Van', 'Gas_Truck', 'Cargo_Bike'
    emission_factor_g_km: float = 185.0  # g CO2 per km (EV = 0 direct, Diesel Van = ~185, Cargo Bike = 0)
    avg_speed_kmh: float = 35.0          # Average speed in city traffic
    cost_per_km: float = 1.2             # USD or INR cost per km
    cost_per_hour: float = 15.0          # Driver + operational hourly cost
    battery_range_km: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "type": self.vehicle_type,
            "emission_factor": self.emission_factor_g_km,
            "avg_speed": self.avg_speed_kmh,
            "cost_per_km": self.cost_per_km
        }


class RoutingProblem:
    """
    Mathematical and geographical representation of the Vehicle Routing Problem.
    Computes Euclidean/Haversine distance matrices and applies dynamic traffic multipliers.
    """

    def __init__(
        self,
        nodes: List[DeliveryNode],
        vehicles: List[Vehicle],
        traffic_multipliers: Optional[np.ndarray] = None,
        use_haversine: bool = True
    ):
        self.nodes = nodes
        self.vehicles = vehicles
        self.num_nodes = len(nodes)
        self.num_vehicles = len(vehicles)
        self.use_haversine = use_haversine

        # Ensure depot exists (node at index 0 is default depot)
        if not any(n.is_depot for n in self.nodes):
            self.nodes[0].is_depot = True

        self.depot_idx = next(i for i, n in enumerate(self.nodes) if n.is_depot)
        
        # Calculate base distance matrix
        self.base_distance_matrix = self._compute_distance_matrix()

        # Traffic congestion multiplier (1.0 = normal, 1.5 = congested, 2.0 = gridlock)
        if traffic_multipliers is not None:
            self.traffic_matrix = traffic_multipliers
        else:
            self.traffic_matrix = np.ones((self.num_nodes, self.num_nodes))

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Computes distance in kilometers between two geo-coordinates."""
        R = 6371.0  # Earth radius in km
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = (
            np.sin(dlat / 2.0) ** 2
            + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0) ** 2
        )
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        return float(R * c)

    def _compute_distance_matrix(self) -> np.ndarray:
        matrix = np.zeros((self.num_nodes, self.num_nodes))
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                if i == j:
                    matrix[i][j] = 0.0
                else:
                    if self.use_haversine:
                        dist = self._haversine_distance(
                            self.nodes[i].lat, self.nodes[i].lon,
                            self.nodes[j].lat, self.nodes[j].lon
                        )
                    else:
                        dx = self.nodes[i].lat - self.nodes[j].lat
                        dy = self.nodes[i].lon - self.nodes[j].lon
                        dist = np.sqrt(dx * dx + dy * dy)
                    matrix[i][j] = dist
        return matrix

    @property
    def effective_distance_matrix(self) -> np.ndarray:
        """Returns distance matrix adjusted for dynamic traffic conditions."""
        return self.base_distance_matrix * self.traffic_matrix

    def get_travel_time_matrix(self, vehicle: Vehicle) -> np.ndarray:
        """Returns travel time in minutes between all pairs of nodes."""
        dist = self.effective_distance_matrix
        # time in hours = dist / speed, in minutes = (dist / speed) * 60
        return (dist / max(1.0, vehicle.avg_speed_kmh)) * 60.0

    def total_demand(self) -> float:
        """Total cargo demand excluding the depot."""
        return sum(n.demand for n in self.nodes if not n.is_depot)

    def total_fleet_capacity(self) -> float:
        """Total capacity across all available vehicles."""
        return sum(v.capacity for v in self.vehicles)
