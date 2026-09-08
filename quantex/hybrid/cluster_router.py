"""
Hybrid Quantum-Classical Clustering & Routing Engine for Multi-Vehicle Fleets (CVRP).
Decomposes large delivery networks into vehicle clusters and routes each cluster using Quantum Solvers.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from quantex.core.problem_model import RoutingProblem, Vehicle, DeliveryNode
from quantex.core.qubo_formulator import QUBOFormulator
from quantex.quantum.qaoa_solver import QAOASolver
from quantex.quantum.vqe_solver import VQESolver
from quantex.quantum.quantum_inspired import QuantumInspiredSolver
from quantex.classical.classical_solvers import ClassicalSolvers
from quantex.core.emissions import GreenLogisticsEngine


def numpy_kmeans(coords: np.ndarray, k: int, max_iter: int = 50, seed: int = 42) -> np.ndarray:
    """
    Pure NumPy implementation of K-Means clustering.
    Zero external dependencies, fast and memory-efficient.
    """
    n = coords.shape[0]
    if n <= k:
        return np.arange(n)

    rng = np.random.RandomState(seed)
    # Initialize centroids randomly from points
    centroids = coords[rng.choice(n, k, replace=False)].copy()
    labels = np.zeros(n, dtype=int)

    for _ in range(max_iter):
        # Calculate distances from each point to each centroid
        # shape: (n, k)
        distances = np.linalg.norm(coords[:, np.newaxis, :] - centroids[np.newaxis, :, :], axis=2)
        new_labels = np.argmin(distances, axis=1)

        if np.array_equal(labels, new_labels):
            break
        labels = new_labels

        # Recompute centroids
        for cluster_idx in range(k):
            members = coords[labels == cluster_idx]
            if len(members) > 0:
                centroids[cluster_idx] = np.mean(members, axis=0)

    return labels


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
            clusters = [[] for _ in range(num_vehicles)]
            for idx, node_idx in enumerate(non_depot_indices):
                clusters[idx % num_vehicles].append(node_idx)
            return clusters

        # Coordinate-based pure NumPy K-Means clustering
        coords = np.array([[problem.nodes[i].lat, problem.nodes[i].lon] for i in non_depot_indices])
        n_clusters = min(num_vehicles, len(non_depot_indices))
        labels = numpy_kmeans(coords, k=n_clusters)

        clusters = [[] for _ in range(num_vehicles)]
        for node_idx, label in zip(non_depot_indices, labels):
            clusters[label].append(node_idx)

        # Re-balance if capacity exceeded
        for v_idx, cluster in enumerate(clusters):
            v_cap = problem.vehicles[v_idx].capacity
            cluster_demand = sum(problem.nodes[i].demand for i in cluster)
            if cluster_demand > v_cap and len(clusters) > 1:
                while cluster_demand > v_cap and len(cluster) > 1:
                    moved_node = cluster.pop()
                    cluster_demand -= problem.nodes[moved_node].demand
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
            solver = QAOASolver(reps=self.qaoa_reps, max_iter=40)
            res = solver.solve(H_c, offset=ising_offset, num_nodes=k, fix_depot=True)
            sub_route = res["optimal_route"]
            info = {
                "solver": res.get("solver", "QAOA"),
                "num_qubits": res.get("num_qubits", (k-1)*(k-1)),
                "optimal_energy": res.get("optimal_energy", 0.0),
                "runtime_sec": res.get("runtime_sec", 0.0),
                "convergence": res.get("convergence", []),
                "state_distribution": res.get("state_distribution", {}),
                "circuit": res.get("circuit")
            }

        elif self.quantum_backend == "vqe" and k <= self.max_cluster_size_quantum:
            H_c, ising_offset = QUBOFormulator.get_sparse_pauli_op(Q, offset)
            solver = VQESolver(reps=2, max_iter=40)
            res = solver.solve(H_c, offset=ising_offset, num_nodes=k, fix_depot=True)
            sub_route = res["optimal_route"]
            info = {
                "solver": res.get("solver", "VQE"),
                "num_qubits": res.get("num_qubits", (k-1)*(k-1)),
                "optimal_energy": res.get("optimal_energy", 0.0),
                "runtime_sec": res.get("runtime_sec", 0.0),
                "convergence": res.get("convergence", []),
                "state_distribution": res.get("state_distribution", {}),
                "circuit": res.get("circuit")
            }

        else:
            # Scalable Quantum-Inspired Annealing (QISA)
            qisa = QuantumInspiredSolver(num_sweeps=250)
            res = qisa.solve(Q, offset=offset, num_nodes=k)
            route_decoded, _ = QUBOFormulator.decode_tsp_solution(res["bitstring"], num_nodes=k, fix_depot=True)
            sub_route = route_decoded
            info = {
                "solver": "Quantum-Inspired Simulated Annealing (QISA)",
                "num_qubits": (k-1)*(k-1),
                "optimal_energy": res.get("energy", 0.0),
                "runtime_sec": res.get("runtime_sec", 0.0),
                "convergence": res.get("convergence", []),
                "state_distribution": {res.get("bitstring", "0"*((k-1)*(k-1))): 1.0}
            }

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
