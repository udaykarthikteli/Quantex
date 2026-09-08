"""
Quantex: FastAPI Backend Server for Render Deployment.
Provides REST API endpoints for Quantum QAOA, VQE, and QISA vehicle routing optimization,
dynamic re-routing, multi-solver benchmarks, and serves the custom animated UI.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import numpy as np
import os
import time

from quantex.data.presets import PRESETS
from quantex.core.problem_model import RoutingProblem, DeliveryNode, Vehicle
from quantex.core.qubo_formulator import QUBOFormulator
from quantex.quantum.circuit_builder import QuantumCircuitBuilder
from quantex.quantum.qaoa_solver import QAOASolver
from quantex.quantum.vqe_solver import VQESolver
from quantex.quantum.quantum_inspired import QuantumInspiredSolver
from quantex.hybrid.cluster_router import HybridClusterRouter
from quantex.hybrid.dynamic_replanner import DynamicLogisticsReplanner
from quantex.classical.classical_solvers import ClassicalSolvers
from quantex.core.emissions import GreenLogisticsEngine

app = FastAPI(
    title="Quantex Quantum Fleet Engine",
    description="Qiskit Quantum Fleet & Last-Mile Logistics Optimization Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active problem state memory for session
ACTIVE_SESSIONS: Dict[str, Any] = {}


def get_default_problem(preset_name: str = "E-Commerce Last-Mile Express") -> RoutingProblem:
    if preset_name in PRESETS:
        return PRESETS[preset_name]()
    return PRESETS["E-Commerce Last-Mile Express"]()


# ---------------- API REQUEST MODELS ----------------
class OptimizeRequest(BaseModel):
    preset_name: str = "E-Commerce Last-Mile Express"
    solver_type: str = "qaoa"  # 'qaoa', 'vqe', 'qisa'
    qaoa_reps: int = 1
    optimizer: str = "COBYLA"
    traffic_multiplier: float = 1.0


class InjectOrderRequest(BaseModel):
    name: str = "Urgent Delivery"
    lat: float
    lon: float
    demand: float = 2.0
    priority: int = 5
    solver_type: str = "qaoa"


class InjectTrafficRequest(BaseModel):
    from_node: int
    to_node: int
    congestion_factor: float = 3.0
    solver_type: str = "qaoa"


# ---------------- REST ENDPOINTS ----------------

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Quantex Quantum Engine", "version": "2.0.0"}


@app.get("/api/presets")
def list_presets():
    """Returns list of available presets and details."""
    result = {}
    for name, func in PRESETS.items():
        prob = func()
        result[name] = {
            "num_nodes": len(prob.nodes),
            "num_vehicles": len(prob.vehicles),
            "depot": prob.nodes[prob.depot_idx].to_dict(),
            "nodes": [n.to_dict() for n in prob.nodes],
            "vehicles": [v.to_dict() for v in prob.vehicles]
        }
    return result


@app.post("/api/optimize")
def optimize_fleet(req: OptimizeRequest):
    """Executes Quantum or Classical Optimization on selected scenario."""
    prob = get_default_problem(req.preset_name)
    
    # Apply traffic multiplier
    if req.traffic_multiplier > 1.0:
        prob.traffic_matrix = np.full((prob.num_nodes, prob.num_nodes), req.traffic_multiplier)

    router = HybridClusterRouter(
        quantum_backend=req.solver_type.lower(),
        qaoa_reps=req.qaoa_reps
    )
    
    res = router.solve_cvrp(prob)
    
    # Cache problem and replanner for session
    session_id = "default"
    ACTIVE_SESSIONS[session_id] = {
        "problem": prob,
        "replanner": DynamicLogisticsReplanner(prob, res["routes"], quantum_backend=req.solver_type.lower())
    }

    # Extract circuit telemetry if available
    telemetry = None
    ascii_circuit = None
    convergence = []
    state_dist = {}

    if res.get("sub_solvers") and "circuit" in res["sub_solvers"][0]:
        first_sub = res["sub_solvers"][0]
        qc = first_sub["circuit"]
        telemetry = QuantumCircuitBuilder.get_circuit_telemetry(qc)
        ascii_circuit = QuantumCircuitBuilder.draw_circuit_ascii(qc)
        convergence = first_sub.get("convergence", [])
        state_dist = first_sub.get("state_distribution", {})

    return {
        "preset_name": req.preset_name,
        "solver": req.solver_type,
        "nodes": [n.to_dict() for n in prob.nodes],
        "vehicles": [v.to_dict() for v in prob.vehicles],
        "routes": res["routes"],
        "fleet_sustainability": res["fleet_sustainability"],
        "aggregated_metrics": res["aggregated_metrics"],
        "baseline_comparison": res["baseline_comparison"],
        "telemetry": telemetry,
        "ascii_circuit": ascii_circuit,
        "convergence": convergence,
        "state_distribution": state_dist
    }


@app.post("/api/dynamic/inject-order")
def inject_order(req: InjectOrderRequest):
    session = ACTIVE_SESSIONS.get("default")
    if not session or not session.get("replanner"):
        prob = get_default_problem()
        router = HybridClusterRouter(quantum_backend=req.solver_type)
        res = router.solve_cvrp(prob)
        replanner = DynamicLogisticsReplanner(prob, res["routes"], quantum_backend=req.solver_type)
        session = {"problem": prob, "replanner": replanner}
        ACTIVE_SESSIONS["default"] = session

    replanner: DynamicLogisticsReplanner = session["replanner"]
    updated_prob, new_routes, ev_info = replanner.inject_urgent_order(
        name=req.name,
        lat=req.lat,
        lon=req.lon,
        demand=req.demand,
        priority=req.priority
    )

    router = HybridClusterRouter(quantum_backend=req.solver_type)
    cvrp_res = router.solve_cvrp(updated_prob)
    session["problem"] = updated_prob

    return {
        "message": f"Order successfully assigned to {ev_info['assigned_vehicle']}",
        "event_info": ev_info,
        "nodes": [n.to_dict() for n in updated_prob.nodes],
        "vehicles": [v.to_dict() for v in updated_prob.vehicles],
        "routes": cvrp_res["routes"],
        "fleet_sustainability": cvrp_res["fleet_sustainability"],
        "aggregated_metrics": cvrp_res["aggregated_metrics"],
        "baseline_comparison": cvrp_res["baseline_comparison"]
    }


@app.post("/api/dynamic/traffic")
def inject_traffic(req: InjectTrafficRequest):
    session = ACTIVE_SESSIONS.get("default")
    if not session or not session.get("replanner"):
        prob = get_default_problem()
        router = HybridClusterRouter(quantum_backend=req.solver_type)
        res = router.solve_cvrp(prob)
        replanner = DynamicLogisticsReplanner(prob, res["routes"], quantum_backend=req.solver_type)
        session = {"problem": prob, "replanner": replanner}
        ACTIVE_SESSIONS["default"] = session

    replanner: DynamicLogisticsReplanner = session["replanner"]
    updated_prob, new_routes, cvrp_res = replanner.inject_traffic_incident(
        from_node=req.from_node,
        to_node=req.to_node,
        congestion_factor=req.congestion_factor
    )
    session["problem"] = updated_prob

    return {
        "message": f"Corridor Node {req.from_node} <-> Node {req.to_node} congested ({req.congestion_factor}x). Quantum fleet re-routed.",
        "nodes": [n.to_dict() for n in updated_prob.nodes],
        "vehicles": [v.to_dict() for v in updated_prob.vehicles],
        "routes": cvrp_res["routes"],
        "fleet_sustainability": cvrp_res["fleet_sustainability"],
        "aggregated_metrics": cvrp_res["aggregated_metrics"],
        "baseline_comparison": cvrp_res["baseline_comparison"]
    }


@app.get("/api/benchmark")
def run_benchmark(preset_name: str = "E-Commerce Last-Mile Express"):
    prob = get_default_problem(preset_name)
    solvers = ["classical", "qaoa", "vqe", "qisa"]
    benchmark_results = []

    for s in solvers:
        if s == "classical":
            router = HybridClusterRouter(quantum_backend="qisa")
            res = router.solve_cvrp(prob)
            m = res["baseline_comparison"]
            dist = res["aggregated_metrics"]["distance_km"] + m["distance_saved_km"]
            co2 = res["aggregated_metrics"]["co2_emissions_kg"] + m["co2_saved_kg"]
            cost = res["aggregated_metrics"]["total_operational_cost"] + m["cost_saved_usd"]
            benchmark_results.append({
                "name": "Classical Greedy (Nearest Neighbor)",
                "distance_km": round(dist, 2),
                "co2_kg": round(co2, 2),
                "cost_usd": round(cost, 2),
                "type": "Classical",
                "color": "#94A3B8"
            })
        elif s == "qaoa":
            router = HybridClusterRouter(quantum_backend="qaoa", qaoa_reps=1)
            t0 = time.time()
            res = router.solve_cvrp(prob)
            t_exec = time.time() - t0
            m = res["aggregated_metrics"]
            benchmark_results.append({
                "name": "Qiskit QAOA (p=1)",
                "distance_km": m["distance_km"],
                "co2_kg": m["co2_emissions_kg"],
                "cost_usd": m["total_operational_cost"],
                "runtime_sec": round(t_exec, 3),
                "type": "Quantum",
                "color": "#8B5CF6"
            })
        elif s == "vqe":
            router = HybridClusterRouter(quantum_backend="vqe", qaoa_reps=2)
            t0 = time.time()
            res = router.solve_cvrp(prob)
            t_exec = time.time() - t0
            m = res["aggregated_metrics"]
            benchmark_results.append({
                "name": "Qiskit VQE (TwoLocal)",
                "distance_km": m["distance_km"],
                "co2_kg": m["co2_emissions_kg"],
                "cost_usd": m["total_operational_cost"],
                "runtime_sec": round(t_exec, 3),
                "type": "Quantum",
                "color": "#3B82F6"
            })
        elif s == "qisa":
            router = HybridClusterRouter(quantum_backend="qisa")
            t0 = time.time()
            res = router.solve_cvrp(prob)
            t_exec = time.time() - t0
            m = res["aggregated_metrics"]
            benchmark_results.append({
                "name": "Quantum-Inspired Annealing (QISA)",
                "distance_km": m["distance_km"],
                "co2_kg": m["co2_emissions_kg"],
                "cost_usd": m["total_operational_cost"],
                "runtime_sec": round(t_exec, 3),
                "type": "Quantum-Inspired",
                "color": "#10B981"
            })

    return {"preset": preset_name, "benchmark": benchmark_results}


# Mount static directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Quantex Quantum Engine</h1><p>Static files loading...</p>")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
