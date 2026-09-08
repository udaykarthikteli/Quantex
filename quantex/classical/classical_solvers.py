"""
Classical Solvers and Benchmarks: Exact DP/Brute Force, 2-Opt, Nearest Neighbor, and Clarke-Wright.
Provides ground-truth baseline comparison against quantum solutions.
"""

from typing import Dict, List, Tuple, Optional
import itertools
import numpy as np
import time


class ClassicalSolvers:
    """
    Collection of classical algorithms for TSP and Multi-Vehicle Routing (VRP).
    """

    @classmethod
    def compute_route_cost(cls, route: List[int], dist_matrix: np.ndarray) -> float:
        """Calculates total route path distance."""
        cost = 0.0
        for i in range(len(route) - 1):
            cost += dist_matrix[route[i], route[i + 1]]
        return cost

    @classmethod
    def exact_tsp(cls, dist_matrix: np.ndarray) -> Dict[str, any]:
        """
        Exact brute-force solver (guarantees global optimal for small instances N <= 10).
        """
        start_time = time.time()
        n = dist_matrix.shape[0]
        other_nodes = list(range(1, n))

        best_cost = float("inf")
        best_route = None

        for perm in itertools.permutations(other_nodes):
            route = [0] + list(perm) + [0]
            cost = cls.compute_route_cost(route, dist_matrix)
            if cost < best_cost:
                best_cost = cost
                best_route = route

        runtime = time.time() - start_time
        return {
            "solver": "Classical Exact (Brute Force)",
            "optimal_route": best_route,
            "optimal_cost": round(best_cost, 4),
            "runtime_sec": round(runtime, 4)
        }

    @classmethod
    def nearest_neighbor(cls, dist_matrix: np.ndarray) -> Dict[str, any]:
        """
        Greedy Nearest Neighbor heuristic.
        """
        start_time = time.time()
        n = dist_matrix.shape[0]
        unvisited = set(range(1, n))
        current = 0
        route = [0]

        while unvisited:
            next_node = min(unvisited, key=lambda x: dist_matrix[current, x])
            route.append(next_node)
            unvisited.remove(next_node)
            current = next_node

        route.append(0)
        cost = cls.compute_route_cost(route, dist_matrix)
        runtime = time.time() - start_time

        return {
            "solver": "Classical Greedy (Nearest Neighbor)",
            "optimal_route": route,
            "optimal_cost": round(cost, 4),
            "runtime_sec": round(runtime, 4)
        }

    @classmethod
    def two_opt(cls, dist_matrix: np.ndarray, initial_route: Optional[List[int]] = None) -> Dict[str, any]:
        """
        2-Opt local search improvement.
        """
        start_time = time.time()
        if initial_route is None:
            initial_route = cls.nearest_neighbor(dist_matrix)["optimal_route"]

        best_route = list(initial_route)
        best_cost = cls.compute_route_cost(best_route, dist_matrix)
        improved = True

        while improved:
            improved = False
            for i in range(1, len(best_route) - 2):
                for j in range(i + 1, len(best_route) - 1):
                    # 2-opt swap
                    new_route = best_route[:i] + best_route[i:j + 1][::-1] + best_route[j + 1:]
                    new_cost = cls.compute_route_cost(new_route, dist_matrix)
                    if new_cost < best_cost - 1e-6:
                        best_route = new_route
                        best_cost = new_cost
                        improved = True
                        break
                if improved:
                    break

        runtime = time.time() - start_time
        return {
            "solver": "Classical Metaheuristic (2-Opt)",
            "optimal_route": best_route,
            "optimal_cost": round(best_cost, 4),
            "runtime_sec": round(runtime, 4)
        }
