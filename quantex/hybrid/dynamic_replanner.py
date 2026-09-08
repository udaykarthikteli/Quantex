"""
Dynamic Real-Time Logistics Re-planner.
Handles on-the-fly events (urgent mid-route orders, traffic jams) and triggers quantum re-routing.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from quantex.core.problem_model import RoutingProblem, DeliveryNode, Vehicle
from quantex.hybrid.cluster_router import HybridClusterRouter


class DynamicLogisticsReplanner:
    """
    Manages live dispatch states and re-routes active vehicles when events occur.
    """

    def __init__(self, problem: RoutingProblem, initial_routes: List[List[int]], quantum_backend: str = "qaoa"):
        self.problem = problem
        self.current_routes = [list(r) for r in initial_routes]
        self.quantum_backend = quantum_backend

    def inject_urgent_order(
        self,
        name: str,
        lat: float,
        lon: float,
        demand: float = 2.0,
        priority: int = 5
    ) -> Tuple[RoutingProblem, List[List[int]], Dict[str, Any]]:
        """
        Dynamically adds an urgent order to the problem and re-optimizes the best vehicle's route.
        """
        new_node_id = len(self.problem.nodes)
        new_node = DeliveryNode(
            id=new_node_id,
            name=name,
            lat=lat,
            lon=lon,
            demand=demand,
            priority=priority
        )
        
        # Add new node to problem
        updated_nodes = list(self.problem.nodes) + [new_node]
        updated_problem = RoutingProblem(
            nodes=updated_nodes,
            vehicles=self.problem.vehicles,
            use_haversine=self.problem.use_haversine
        )

        # Find best vehicle cluster to insert the new node based on distance and capacity
        best_v_idx = 0
        min_insert_dist = float("inf")
        depot_idx = updated_problem.depot_idx

        for v_idx, route in enumerate(self.current_routes):
            # Check capacity
            current_v_load = sum(updated_problem.nodes[n].demand for n in route if n != depot_idx)
            if current_v_load + demand <= updated_problem.vehicles[v_idx].capacity:
                # Calculate minimum distance from new node to any node in current route
                for node_id in route:
                    d = updated_problem.effective_distance_matrix[node_id, new_node_id]
                    if d < min_insert_dist:
                        min_insert_dist = d
                        best_v_idx = v_idx

        # Re-solve the target vehicle's cluster with quantum solver
        target_cluster = [n for n in self.current_routes[best_v_idx] if n != depot_idx] + [new_node_id]
        
        router = HybridClusterRouter(quantum_backend=self.quantum_backend)
        new_v_route, new_cost, telemetry = router.route_cluster_quantum(target_cluster, updated_problem)

        new_all_routes = list(self.current_routes)
        new_all_routes[best_v_idx] = new_v_route

        self.problem = updated_problem
        self.current_routes = new_all_routes

        return updated_problem, new_all_routes, {
            "assigned_vehicle": self.problem.vehicles[best_v_idx].name,
            "new_route": new_v_route,
            "cost": new_cost,
            "telemetry": telemetry
        }

    def inject_traffic_incident(
        self,
        from_node: int,
        to_node: int,
        congestion_factor: float = 3.0
    ) -> Tuple[RoutingProblem, List[List[int]], Dict[str, Any]]:
        """
        Simulates sudden traffic congestion on a specific road edge and re-optimizes.
        """
        traffic_matrix = np.copy(self.problem.traffic_matrix)
        traffic_matrix[from_node, to_node] = congestion_factor
        traffic_matrix[to_node, from_node] = congestion_factor

        updated_problem = RoutingProblem(
            nodes=self.problem.nodes,
            vehicles=self.problem.vehicles,
            traffic_multipliers=traffic_matrix,
            use_haversine=self.problem.use_haversine
        )

        # Re-solve all routes with updated traffic
        router = HybridClusterRouter(quantum_backend=self.quantum_backend)
        cvrp_res = router.solve_cvrp(updated_problem)

        self.problem = updated_problem
        self.current_routes = cvrp_res["routes"]

        return updated_problem, cvrp_res["routes"], cvrp_res
