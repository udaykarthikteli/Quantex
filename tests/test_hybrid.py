"""
Unit tests for Hybrid Quantum CVRP clustering, green emissions, and dynamic replanning.
"""

import pytest
from quantex.data.presets import get_ecommerce_preset, get_field_services_preset
from quantex.hybrid.cluster_router import HybridClusterRouter
from quantex.hybrid.dynamic_replanner import DynamicLogisticsReplanner
from quantex.core.emissions import GreenLogisticsEngine


def test_hybrid_cvrp():
    problem = get_ecommerce_preset()
    router = HybridClusterRouter(quantum_backend="qaoa", qaoa_reps=1, max_cluster_size_quantum=4)
    res = router.solve_cvrp(problem)

    assert "routes" in res
    assert len(res["routes"]) == len(problem.vehicles)
    assert "fleet_sustainability" in res
    assert "baseline_comparison" in res
    assert res["aggregated_metrics"]["distance_km"] > 0


def test_dynamic_replanner():
    problem = get_field_services_preset()
    router = HybridClusterRouter(quantum_backend="qaoa", qaoa_reps=1)
    res = router.solve_cvrp(problem)

    replanner = DynamicLogisticsReplanner(problem, res["routes"], quantum_backend="qaoa")
    updated_prob, new_routes, info = replanner.inject_urgent_order(
        name="Emergency Substation Repair",
        lat=17.7450,
        lon=83.3150,
        demand=1.0,
        priority=5
    )

    assert len(updated_prob.nodes) == len(problem.nodes) + 1
    assert "assigned_vehicle" in info
