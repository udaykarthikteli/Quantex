"""
Hybrid Quantum-Classical Clustering & Routing Engine for Multi-Vehicle Fleets (CVRP).
Decomposes large delivery networks into vehicle clusters and routes each cluster using Quantum Solvers.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from sklearn.cluster import KMeans

from quantex.core.problem_model import RoutingProblem, Vehicle, DeliveryNode
from quantex.core.qubo_formulator import QUBOFormulator
from quantex.quantum.qaoa_solver import QAOASolver
from quantex.quantum.vqe_solver import VQESolver
from quantex.quantum.quantum_inspired import QuantumInspiredSolver
from quantex.classical.classical_solvers import ClassicalSolvers
from quantex.core.emissions import GreenLogisticsEngine


class HybridClusterRouter:
    """
    Solves Capacitated Multi-Vehicle Routing Problem (CVRP) by:
    1. Clustering delivery stops across vehicles using capacity-aware clustering.
    2. Solving each sub-problem on a Quantum solver (QAOA / VQE / Quantum-Inspired).
    3. Aggregating multi-fleet schedule and environmental metrics.
    """

    def __init__(self, quantum_backend: str = "qaoa", qaoa_reps: int = 1, max_cluster_size_quantum: int = 5):
        self.quantum_backend = quantum_backend.lower()
        self.qaoa_reps = qaoa_reps
        self.max_cluster_size_quantum = max_cluster_size_quantum

    def cluster_nodes_for_fleet(self, problem: RoutingProblem) -> List[List[int]]:
        """
        Partitions delivery nodes among available vehicles respecting capacities.
        """
        non_depot_indices = [i for i, n in enumerate(problem.nodes) if not n.is_depot]
        num_vehicles = len(problem.vehicles)

        if not non_depot_indices:
            return [[problem.depot_idx] for _ in range(num_vehicles)]

        if num_vehicles == 1 or len(non_depot_indices) <= num_vehicles:
            # Simple division
            clusters = [[] for _ in range(num_vehicles)]
            for idx, node_idx in enumerate(non_depot_indices):
                clusters[idx % num_vehicles].append(node_idx)
            return clusters

        # Coordinate-based K-Means clustering
        coords = np.array([[problem.nodes[i].lat, problem.nodes[i].lon] for i in non_depot_indices])
        n_clusters = min(num_vehicles, len(non_depot_indices))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(coords)

        clusters = [[] for _ in range(num_vehicles)]
        for node_idx, label in zip(non_depot_indices, labels):
            clusters[label].append(node_idx)

        # Re-balance if capacity exceeded
        for v_idx, cluster in enumerate(clusters):
            v_cap = problem.vehicles[v_idx].capacity
            cluster_demand = sum(problem.nodes[i].demand for i in cluster)
            if cluster_demand > v_cap and len(clusters) > 1:
                # Move excess demand to next available vehicle with space
                while cluster_demand > v_cap and len(cluster) > 1:
                    moved_node = cluster.pop()
                    cluster_demand -= problem.nodes[moved_node].demand
                    # Find vehicle with least load
                    other_v = min(
                        [i for i in range(num_vehicles) if i != v_idx],
                        key=lambda x: sum(problem.nodes[n].demand for n in clusters[x])
                    )
                    clusters[other_v].append(moved_node)

        return clusters

    def route_cluster_quantum(
        self,
        cluster_node_indices: List[int],
        problem: RoutingProblem
    ) -> Tuple[List[int], float, Dict[str, Any]]:
        """
        Solves a single sub-route (depot + cluster nodes) using quantum solver.
        """
        sub_indices = [problem.depot_idx] + cluster_node_indices
        k = len(sub_indices)

        if k <= 2:
            route = sub_indices + [problem.depot_idx] if k == 2 else [problem.depot_idx, problem.depot_idx]
            cost = ClassicalSolvers.compute_route_cost(route, problem.effective_distance_matrix)
            return route, cost, {"solver": "Direct"}

        # Sub-distance matrix
        sub_dist = np.zeros((k, k))
        for i_sub, orig_i in enumerate(sub_indices):
            for j_sub, orig_j in enumerate(sub_indices):
                sub_dist[i_sub, j_sub] = problem.effective_distance_matrix[orig_i, orig_j]

        # Use quantum formulation
        Q, offset, _ = QUBOFormulator.build_tsp_qubo(sub_dist, fix_depot=True)

        info = {}
        sub_route = None

        if self.quantum_backend == "qaoa" and k <= self.max_cluster_size_quantum:
            H_c, ising_offset = QUBOFormulator.get_sparse_pauli_op(Q, offset)
            solver = QAOASolver(reps=self.qaoa_reps)
            res = solver.solve(H_c, offset=ising_offset, num_nodes=k, fix_depot=True)
            sub_route = res["optimal_route"]
            info = res

        elif self.quantum_backend == "vqe" and k <= self.max_cluster_size_quantum:
            H_c, ising_offset = QUBOFormulator.get_sparse_pauli_op(Q, offset)
            solver = VQESolver(reps=2)
            res = solver.solve(H_c, offset=ising_offset, num_nodes=k, fix_depot=True)
            sub_route = res["optimal_route"]
            info = res

        else:
            # Scalable Quantum-Inspired Annealing (QISA)
            qisa = QuantumInspiredSolver(num_sweeps=400)
            res = qisa.solve(Q, offset=offset, num_nodes=k)
            route_decoded, _ = QUBOFormulator.decode_tsp_solution(res["bitstring"], num_nodes=k, fix_depot=True)
            sub_route = route_decoded
            info = res

        # Map sub-route back to global node IDs
        global_route = [sub_indices[i] for i in sub_route]
        cost = ClassicalSolvers.compute_route_cost(global_route, problem.effective_distance_matrix)
        return global_route, cost, info

    def solve_cvrp(self, problem: RoutingProblem) -> Dict[str, Any]:
        """
        Runs the full hybrid quantum CVRP optimization pipeline.
        """
        clusters = self.cluster_nodes_for_fleet(problem)
        vehicle_routes = []
        total_quantum_cost = 0.0
        fleet_sustainability = []

        sub_solver_telemetry = []

        for v_idx, cluster in enumerate(clusters):
            vehicle = problem.vehicles[v_idx]
            route, cost, info = self.route_cluster_quantum(cluster, problem)
            vehicle_routes.append(route)
            total_quantum_cost += cost
            sub_solver_telemetry.append(info)

            # Route sustainability metrics
            metrics = GreenLogisticsEngine.evaluate_route_sustainability(route, problem, vehicle)
            metrics["vehicle_id"] = vehicle.id
            metrics["vehicle_name"] = vehicle.name
            metrics["vehicle_type"] = vehicle.vehicle_type
            metrics["route"] = route
            fleet_sustainability.append(metrics)

        # Baseline comparison: greedy multi-vehicle routing
        baseline_fleet = []
        total_baseline_cost = 0.0
        for v_idx, cluster in enumerate(clusters):
            vehicle = problem.vehicles[v_idx]
            sub_indices = [problem.depot_idx] + cluster
            sub_dist = np.zeros((len(sub_indices), len(sub_indices)))
            for i_sub, orig_i in enumerate(sub_indices):
                for j_sub, orig_j in enumerate(sub_indices):
                    sub_dist[i_sub, j_sub] = problem.effective_distance_matrix[orig_i, orig_j]
            greedy_res = ClassicalSolvers.nearest_neighbor(sub_dist)
            greedy_global = [sub_indices[i] for i in greedy_res["optimal_route"]]
            b_metrics = GreenLogisticsEngine.evaluate_route_sustainability(greedy_global, problem, vehicle)
            baseline_fleet.append(b_metrics)
            total_baseline_cost += greedy_res["optimal_cost"]

        # Aggregate total sustainability
        agg_quantum = {
            "distance_km": sum(m["distance_km"] for m in fleet_sustainability),
            "total_time_min": sum(m["total_time_min"] for m in fleet_sustainability),
            "fuel_consumed": sum(m["fuel_consumed"] for m in fleet_sustainability),
            "co2_emissions_kg": sum(m["co2_emissions_kg"] for m in fleet_sustainability),
            "total_operational_cost": sum(m["total_operational_cost"] for m in fleet_sustainability)
        }

        agg_baseline = {
            "distance_km": sum(m["distance_km"] for m in baseline_fleet),
            "total_time_min": sum(m["total_time_min"] for m in baseline_fleet),
            "fuel_consumed": sum(m["fuel_consumed"] for m in baseline_fleet),
            "co2_emissions_kg": sum(m["co2_emissions_kg"] for m in baseline_fleet),
            "total_operational_cost": sum(m["total_operational_cost"] for m in baseline_fleet)
        }

        comparison = GreenLogisticsEngine.compare_solutions(agg_quantum, agg_baseline)

        return {
            "routes": vehicle_routes,
            "fleet_sustainability": fleet_sustainability,
            "aggregated_metrics": agg_quantum,
            "baseline_comparison": comparison,
            "sub_solvers": sub_solver_telemetry
        }
