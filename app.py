"""
Quantex: Quantum-Powered Fleet & Last-Mile Logistics Optimization Platform
Qiskit Fall Fest Hackathon 2026 - Use Case 04 (Vehicle Routing & Last-Mile Delivery)
"""

import streamlit as st
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import time
import json
import io
import subprocess

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

# Streamlit Page Setup
st.set_page_config(
    page_title="Quantex | Quantum Fleet & Logistics Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- ANIMATED QUANTUM BACKGROUND & GLASSMORPHISM CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Animated Aurora & Quantum Particle Canvas Background */
    .stApp {
        background: radial-gradient(ellipse at 20% 20%, rgba(99, 102, 241, 0.18) 0%, transparent 50%),
                    radial-gradient(ellipse at 80% 80%, rgba(236, 72, 153, 0.15) 0%, transparent 50%),
                    radial-gradient(ellipse at 50% 50%, rgba(16, 185, 129, 0.12) 0%, transparent 60%),
                    linear-gradient(180deg, #0a0b10 0%, #10121a 50%, #08090d 100%);
        background-attachment: fixed;
    }

    /* Ambient Floating Glow Keyframes */
    @keyframes pulseGlow {
        0% { filter: drop-shadow(0 0 15px rgba(99, 102, 241, 0.4)); }
        50% { filter: drop-shadow(0 0 25px rgba(139, 92, 246, 0.6)); }
        100% { filter: drop-shadow(0 0 15px rgba(99, 102, 241, 0.4)); }
    }

    @keyframes floatParticle {
        0% { transform: translateY(0px) rotate(0deg); opacity: 0.6; }
        50% { transform: translateY(-12px) rotate(180deg); opacity: 0.9; }
        100% { transform: translateY(0px) rotate(360deg); opacity: 0.6; }
    }

    /* Glassmorphism Header */
    .main-header {
        background: rgba(22, 24, 38, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        padding: 26px 32px;
        border-radius: 18px;
        color: white;
        margin-bottom: 22px;
        border: 1px solid rgba(139, 92, 246, 0.35);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        animation: pulseGlow 4s ease-in-out infinite;
    }

    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(26, 29, 45, 0.65);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 14px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        margin-bottom: 16px;
    }

    .glass-metric {
        background: rgba(30, 34, 56, 0.6);
        backdrop-filter: blur(8px);
        border-radius: 12px;
        padding: 16px;
        border-left: 4px solid #6366F1;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-metric:hover {
        transform: translateY(-2px);
        border-left-color: #10B981;
    }

    /* Badges */
    .badge-qiskit {
        background: linear-gradient(135deg, #6929C4 0%, #8A3FFC 100%);
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 10px rgba(105, 41, 196, 0.4);
    }
    .badge-green {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 10px rgba(16, 185, 129, 0.4);
    }
    .badge-quantum {
        background: linear-gradient(135deg, #2563EB 0%, #38BDF8 100%);
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.5px;
    }

    /* Custom Streamlit Metric & Tabs Styling */
    div[data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #F8FAFC !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(18, 20, 32, 0.7);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #94A3B8;
        font-weight: 600;
        padding: 8px 18px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #4F46E5 !important;
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)


# Animated Quantum Waves & Entanglement Particles Canvas in Streamlit Background
st.components.v1.html("""
<canvas id="quantum-bg" style="position:fixed; top:0; left:0; width:100vw; height:100vh; pointer-events:none; z-index:0; opacity:0.35;"></canvas>
<script>
    const canvas = document.getElementById('quantum-bg');
    const ctx = canvas.getContext('2d');
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });

    const particles = [];
    const numParticles = 45;
    const colors = ['#6366F1', '#8B5CF6', '#EC4899', '#10B981', '#38BDF8'];

    for (let i = 0; i < numParticles; i++) {
        particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            radius: Math.random() * 2.5 + 1.2,
            color: colors[Math.floor(Math.random() * colors.length)],
            vx: (Math.random() - 0.5) * 0.7,
            vy: (Math.random() - 0.5) * 0.7,
            phase: Math.random() * Math.PI * 2
        });
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);
        
        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.phase += 0.02;

            if (p.x < 0) p.x = width;
            if (p.x > width) p.x = 0;
            if (p.y < 0) p.y = height;
            if (p.y > height) p.y = 0;

            // Quantum particle superposition pulse
            const currentRadius = p.radius + Math.sin(p.phase) * 0.8;
            ctx.beginPath();
            ctx.arc(p.x, p.y, Math.max(0.5, currentRadius), 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.shadowBlur = 12;
            ctx.shadowColor = p.color;
            ctx.fill();

            // Quantum entanglement connections
            for (let j = i + 1; j < particles.length; j++) {
                const p2 = particles[j];
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 130) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = p.color;
                    ctx.globalAlpha = (1 - dist / 130) * 0.25;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                    ctx.globalAlpha = 1.0;
                }
            }
        }
        requestAnimationFrame(animate);
    }
    animate();
</script>
""", height=0)


def init_session_state():
    if "current_preset" not in st.session_state:
        st.session_state.current_preset = "E-Commerce Last-Mile Express"
    if "problem" not in st.session_state:
        st.session_state.problem = PRESETS[st.session_state.current_preset]()
    if "optimization_results" not in st.session_state:
        st.session_state.optimization_results = None
    if "replanner" not in st.session_state:
        st.session_state.replanner = None


init_session_state()

# ----------------- SIDEBAR CONTROLS -----------------
with st.sidebar:
    st.image("https://raw.githubusercontent.com/Qiskit/qiskit/main/docs/_static/qiskit-logo.png", width=180)
    st.markdown("### ⚡ **Quantex Control Hub**")
    st.caption("Centurion University • Qiskit Fall Fest 2026")
    st.divider()

    # Preset selection
    preset_choice = st.selectbox(
        "📁 Select Logistics Domain:",
        list(PRESETS.keys()),
        index=list(PRESETS.keys()).index(st.session_state.current_preset)
    )

    if preset_choice != st.session_state.current_preset:
        st.session_state.current_preset = preset_choice
        st.session_state.problem = PRESETS[preset_choice]()
        st.session_state.optimization_results = None
        st.session_state.replanner = None
        st.rerun()

    st.divider()
    st.markdown("#### ⚛️ **Quantum Solver Engine**")
    solver_type = st.selectbox(
        "Algorithm Backend:",
        ["QAOA (Quantum Approximate Optimization)", "VQE (Variational Quantum Eigensolver)", "Quantum-Inspired Annealing (QISA)"]
    )

    qaoa_reps = 1
    optimizer_choice = "COBYLA"
    if "QAOA" in solver_type:
        qaoa_reps = st.slider("QAOA Circuit Depth (p-reps):", min_value=1, max_value=3, value=1, help="Number of alternating cost and mixer Hamiltonian layers.")
        optimizer_choice = st.selectbox("Classical Optimizer:", ["COBYLA", "SLSQP", "Nelder-Mead"])
    elif "VQE" in solver_type:
        vqe_ansatz = st.selectbox("Ansatz Architecture:", ["two_local", "real_amplitudes"])
        vqe_reps = st.slider("Ansatz Entanglement Reps:", min_value=1, max_value=3, value=2)

    st.divider()
    st.markdown("#### 🚦 **Traffic & Fleet Parameters**")
    traffic_surge = st.slider("Live Congestion Multiplier:", 1.0, 3.0, 1.0, 0.1, help="Multiplies travel times and road resistance.")
    
    st.divider()
    run_btn = st.button("🚀 Run Quantum Optimization", type="primary", use_container_width=True)


# ----------------- MAIN UI BANNER -----------------
st.markdown("""
<div class="main-header">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div>
            <h1 style="margin:0; font-size:28px; font-weight:800; letter-spacing:-0.5px;">⚡ Quantex: Quantum Fleet & Last-Mile Delivery Engine</h1>
            <p style="margin:6px 0 0 0; opacity:0.85; font-size:14px; font-weight:400;">
                Capacitated Vehicle Routing (CVRP) & Dynamic Time-Windows powered by Qiskit QAOA, VQE, and Green Fleet Analytics
            </p>
        </div>
        <div style="display:flex; gap:8px;">
            <span class="badge-qiskit">Qiskit v2.5+</span>
            <span class="badge-quantum">Ising QUBO</span>
            <span class="badge-green">Net-Zero Logistics</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# Apply traffic surge if changed
if traffic_surge > 1.0:
    st.session_state.problem.traffic_matrix = np.full(
        (st.session_state.problem.num_nodes, st.session_state.problem.num_nodes), traffic_surge
    )

# Run optimization when clicked or if initial run
if run_btn or st.session_state.optimization_results is None:
    with st.spinner("⚛️ Formulating QUBO Hamiltonian & executing Quantum Optimization..."):
        backend_key = "qaoa"
        if "VQE" in solver_type:
            backend_key = "vqe"
        elif "Quantum-Inspired" in solver_type:
            backend_key = "qisa"

        router = HybridClusterRouter(quantum_backend=backend_key, qaoa_reps=qaoa_reps)
        results = router.solve_cvrp(st.session_state.problem)
        st.session_state.optimization_results = results
        st.session_state.replanner = DynamicLogisticsReplanner(
            st.session_state.problem, results["routes"], quantum_backend=backend_key
        )


results = st.session_state.optimization_results
problem = st.session_state.problem
agg = results["aggregated_metrics"]
comp = results["baseline_comparison"]


# ----------------- TOP GLOWING KPI METRIC CARDS -----------------
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Route Distance", f"{agg['distance_km']:.2f} km", delta=f"-{comp['distance_saved_km']} km saved" if comp['distance_saved_km'] > 0 else "Optimal", delta_color="normal")
with col2:
    st.metric("Fleet Fuel Consumed", f"{agg['fuel_consumed']:.2f} L/kWh", delta=f"-{comp['fuel_saved']} saved" if comp['fuel_saved'] > 0 else "Optimal", delta_color="normal")
with col3:
    st.metric("🌿 CO2 Emissions", f"{agg['co2_emissions_kg']:.2f} kg", delta=f"-{comp['co2_saved_kg']} kg abated" if comp['co2_saved_kg'] > 0 else "Optimal", delta_color="normal")
with col4:
    st.metric("Transit Duration", f"{agg['total_time_min']:.1f} mins", delta=f"-{comp['time_saved_min']} min faster" if comp['time_saved_min'] > 0 else "Optimal", delta_color="normal")
with col5:
    st.metric("Operational Cost", f"${agg['total_operational_cost']:.2f}", delta=f"-${comp['cost_saved_usd']} saved" if comp['cost_saved_usd'] > 0 else "Optimal", delta_color="normal")

st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)


# ----------------- FEATURE TABS -----------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🗺️ Interactive Route Map",
    "🎬 Live Fleet Playback",
    "⚛️ Quantum Circuit & Telemetry",
    "📊 Benchmarking Arena",
    "🚨 Dynamic Event Simulator",
    "🧪 Self-Test & Diagnostic Suite"
])

# ----------------- TAB 1: INTERACTIVE MAP -----------------
with tab1:
    st.markdown("### 🗺️ **Active Fleet Geographical Dispatch & Multi-Vehicle Routes**")
    st.caption("Routes partitioned by Capacity-Aware Clustering and optimized via Qiskit Quantum Solvers.")

    lats = [n.lat for n in problem.nodes]
    lons = [n.lon for n in problem.nodes]
    map_center = [np.mean(lats), np.mean(lons)]

    m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB dark_matter")

    palette = ["#6366F1", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"]

    # Mark Depot
    depot_node = problem.nodes[problem.depot_idx]
    folium.Marker(
        [depot_node.lat, depot_node.lon],
        popup=f"<b>🏢 CENTRAL DEPOT:</b> {depot_node.name}",
        tooltip=f"Depot: {depot_node.name}",
        icon=folium.Icon(color="red", icon="home", prefix="fa")
    ).add_to(m)

    # Mark Customer Nodes
    for node in problem.nodes:
        if not node.is_depot:
            priority_tag = "🔴 High Priority" if node.priority >= 4 else "🟢 Normal"
            folium.Marker(
                [node.lat, node.lon],
                popup=f"""
                <div style='font-family:sans-serif; min-width:180px;'>
                    <h4 style='margin:0 0 6px 0;'>📦 {node.name}</h4>
                    <b>Demand:</b> {node.demand} units<br>
                    <b>Time Window:</b> {node.time_window_start:.0f} - {node.time_window_end:.0f} min<br>
                    <b>Service Time:</b> {node.service_duration:.0f} min<br>
                    <b>Priority:</b> {priority_tag}
                </div>
                """,
                tooltip=f"{node.name} ({node.demand} units)",
                icon=folium.Icon(color="blue", icon="shopping-bag", prefix="fa")
            ).add_to(m)

    # Draw Vehicle Paths
    for v_idx, route in enumerate(results["routes"]):
        if len(route) < 2:
            continue
        v_color = palette[v_idx % len(palette)]
        v_name = problem.vehicles[v_idx].name
        v_type = problem.vehicles[v_idx].vehicle_type

        route_coords = [[problem.nodes[idx].lat, problem.nodes[idx].lon] for idx in route]
        
        folium.PolyLine(
            route_coords,
            color=v_color,
            weight=5,
            opacity=0.9,
            tooltip=f"{v_name} ({v_type})"
        ).add_to(m)

    st_folium(m, width=1150, height=520)


# ----------------- TAB 2: LIVE FLEET PLAYBACK & TRANSIT ANIMATION -----------------
with tab2:
    st.markdown("### 🎬 **Live Fleet Playback & Step-by-Step Dispatch Simulation**")
    st.caption("Simulate real-time vehicle movement, package drop-offs, and payload status along the quantum routes.")

    max_steps = max(len(r) for r in results["routes"]) if results["routes"] else 1
    playback_step = st.slider("⏱️ Route Progress Step:", min_value=1, max_value=max_steps, value=1)

    pcols = st.columns(len(results["routes"]))
    for v_idx, route in enumerate(results["routes"]):
        v = problem.vehicles[v_idx]
        with pcols[v_idx]:
            st.markdown(f"#### 🚚 **{v.name}** (`{v.vehicle_type}`)")
            curr_idx = min(playback_step - 1, len(route) - 1)
            current_stop_id = route[curr_idx]
            current_stop_node = problem.nodes[current_stop_id]
            
            # Calculate remaining payload
            delivered_demand = sum(problem.nodes[route[i]].demand for i in range(1, curr_idx + 1) if route[i] != problem.depot_idx)
            remaining_payload = max(0.0, v.capacity - delivered_demand)

            st.markdown(f"""
            <div class="glass-metric">
                <b>Current Location:</b> {current_stop_node.name}<br>
                <b>Stop Status:</b> {"🏢 At Depot" if current_stop_node.is_depot else "📦 Delivering"}<br>
                <b>Payload Remaining:</b> {remaining_payload:.1f} / {v.capacity:.1f} units<br>
                <b>Progress:</b> Step {curr_idx + 1} of {len(route)}
            </div>
            """, unsafe_allow_html=True)
            
            progress_pct = int(((curr_idx + 1) / len(route)) * 100)
            st.progress(progress_pct)


# ----------------- TAB 3: QUANTUM CIRCUIT & TELEMETRY -----------------
with tab3:
    st.markdown("### ⚛️ **Quantum Circuit Architecture, Qubit Entanglement & Convergence**")
    st.caption("Real-time inspection of Qiskit parameterized ansatz, gate counts, depth, and ground state statevectors.")

    sub_solvers = results.get("sub_solvers", [])
    if sub_solvers and "circuit" in sub_solvers[0]:
        first_solver = sub_solvers[0]
        qc = first_solver["circuit"]
        telemetry = QuantumCircuitBuilder.get_circuit_telemetry(qc)

        qcol1, qcol2, qcol3, qcol4 = st.columns(4)
        with qcol1:
            st.metric("Quantum Qubits (N)", telemetry["num_qubits"])
        with qcol2:
            st.metric("Circuit Depth", telemetry["depth"])
        with qcol3:
            st.metric("CNOT (CX) Entanglement Gates", telemetry["cnot_count"])
        with qcol4:
            st.metric("Variational Parameters (θ/γ/β)", telemetry["num_parameters"])

        st.divider()

        gcol1, gcol2 = st.columns(2)

        with gcol1:
            st.markdown("#### 📉 **Classical Optimizer Convergence ⟨H_c⟩**")
            if "convergence" in first_solver and first_solver["convergence"]:
                evals, costs = zip(*first_solver["convergence"])
                fig_conv = px.line(
                    x=evals, y=costs,
                    labels={"x": "Optimizer Iteration", "y": "Hamiltonian Expectation ⟨H_c⟩"},
                    title="Energy Minimization Trajectory",
                    markers=True
                )
                fig_conv.update_traces(line_color="#818CF8", line_width=3)
                fig_conv.update_layout(template="plotly_dark")
                st.plotly_chart(fig_conv, use_container_width=True)
            else:
                st.info("Direct solver / simulated execution used for this cluster.")

        with gcol2:
            st.markdown("#### 🎯 **Sampled Ground State Distribution |x⟩**")
            if "state_distribution" in first_solver and first_solver["state_distribution"]:
                states_df = pd.DataFrame(
                    list(first_solver["state_distribution"].items()),
                    columns=["Basis State |x⟩", "Probability"]
                ).sort_values(by="Probability", ascending=False).head(10)
                
                fig_dist = px.bar(
                    states_df, x="Basis State |x⟩", y="Probability",
                    color="Probability",
                    color_continuous_scale="Purples",
                    title="Top 10 Computational Basis States"
                )
                fig_dist.update_layout(template="plotly_dark")
                st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown("#### 📜 **Qiskit Parameterized Circuit Schematic (ASCII Output)**")
        ascii_art = QuantumCircuitBuilder.draw_circuit_ascii(qc)
        st.code(ascii_art, language="text")

    else:
        st.info("Quantum telemetry available when sub-cluster routing is performed with QAOA/VQE.")


# ----------------- TAB 4: BENCHMARKING ARENA -----------------
with tab4:
    st.markdown("### 📊 **Quantum vs Classical Solver Benchmarking Arena**")
    st.caption("Live comparative analysis across Classical Greedy (Nearest Neighbor), 2-Opt, QAOA, VQE, and QISA.")

    if st.button("⚡ Execute Live Multi-Solver Benchmark"):
        with st.spinner("Executing Classical Baselines, Qiskit QAOA, VQE, and QISA..."):
            b_data = []

            # 1. Classical Nearest Neighbor
            router_nn = HybridClusterRouter(quantum_backend="qisa")
            res_nn = router_nn.solve_cvrp(problem)
            b_comp = res_nn["baseline_comparison"]
            b_data.append({
                "Algorithm": "Classical Greedy (Nearest Neighbor)",
                "Distance (km)": agg["distance_km"] + b_comp["distance_saved_km"],
                "CO2 (kg)": agg["co2_emissions_kg"] + b_comp["co2_saved_kg"],
                "Cost ($)": agg["total_operational_cost"] + b_comp["cost_saved_usd"],
                "Type": "Classical Baseline"
            })

            # 2. Qiskit QAOA
            router_qaoa = HybridClusterRouter(quantum_backend="qaoa", qaoa_reps=1)
            res_qaoa = router_qaoa.solve_cvrp(problem)
            b_data.append({
                "Algorithm": "Qiskit QAOA (p=1)",
                "Distance (km)": res_qaoa["aggregated_metrics"]["distance_km"],
                "CO2 (kg)": res_qaoa["aggregated_metrics"]["co2_emissions_kg"],
                "Cost ($)": res_qaoa["aggregated_metrics"]["total_operational_cost"],
                "Type": "Quantum"
            })

            # 3. Qiskit VQE
            router_vqe = HybridClusterRouter(quantum_backend="vqe", qaoa_reps=2)
            res_vqe = router_vqe.solve_cvrp(problem)
            b_data.append({
                "Algorithm": "Qiskit VQE (TwoLocal)",
                "Distance (km)": res_vqe["aggregated_metrics"]["distance_km"],
                "CO2 (kg)": res_vqe["aggregated_metrics"]["co2_emissions_kg"],
                "Cost ($)": res_vqe["aggregated_metrics"]["total_operational_cost"],
                "Type": "Quantum"
            })

            # 4. Quantum-Inspired Annealing
            router_qisa = HybridClusterRouter(quantum_backend="qisa")
            res_qisa = router_qisa.solve_cvrp(problem)
            b_data.append({
                "Algorithm": "Quantum-Inspired Annealing (QISA)",
                "Distance (km)": res_qisa["aggregated_metrics"]["distance_km"],
                "CO2 (kg)": res_qisa["aggregated_metrics"]["co2_emissions_kg"],
                "Cost ($)": res_qisa["aggregated_metrics"]["total_operational_cost"],
                "Type": "Quantum-Inspired"
            })

            b_df = pd.DataFrame(b_data)
            st.dataframe(b_df, use_container_width=True)

            b_col1, b_col2 = st.columns(2)
            with b_col1:
                fig_b1 = px.bar(b_df, x="Algorithm", y="Distance (km)", color="Type", title="Total Fleet Travel Distance (Lower is Better)")
                fig_b1.update_layout(template="plotly_dark")
                st.plotly_chart(fig_b1, use_container_width=True)
            with b_col2:
                fig_b2 = px.bar(b_df, x="Algorithm", y="CO2 (kg)", color="Type", title="Total Carbon Emissions (Lower is Better)")
                fig_b2.update_layout(template="plotly_dark")
                st.plotly_chart(fig_b2, use_container_width=True)


# ----------------- TAB 5: DYNAMIC EVENT SIMULATOR -----------------
with tab5:
    st.markdown("### 🚨 **Dynamic Real-Time Logistics Event Simulator**")
    st.caption("Simulate unexpected high-priority customer calls or sudden traffic gridlocks and re-balance fleet via Quantum.")

    dcol1, dcol2 = st.columns(2)

    with dcol1:
        st.markdown("#### 📦 **Inject Urgent Mid-Route Delivery Order**")
        order_name = st.text_input("Customer / Location Name:", "Urgent Medical Sample Pickup")
        order_lat = st.number_input("Latitude:", value=17.7350, format="%.4f")
        order_lon = st.number_input("Longitude:", value=83.3100, format="%.4f")
        order_demand = st.number_input("Cargo Units (kg):", value=5.0, min_value=0.1, max_value=50.0)

        if st.button("⚡ Inject Order & Trigger Quantum Re-dispatch"):
            if st.session_state.replanner is not None:
                with st.spinner("Re-optimizing fleet routes on quantum backend..."):
                    up_prob, new_routes, ev_info = st.session_state.replanner.inject_urgent_order(
                        name=order_name,
                        lat=order_lat,
                        lon=order_lon,
                        demand=order_demand,
                        priority=5
                    )
                    st.session_state.problem = up_prob
                    router = HybridClusterRouter(quantum_backend="qaoa")
                    st.session_state.optimization_results = router.solve_cvrp(up_prob)
                    st.success(f"✅ Order assigned to **{ev_info['assigned_vehicle']}**! Fleet re-routed successfully.")
                    st.rerun()

    with dcol2:
        st.markdown("#### 🚦 **Simulate Road Congestion Surge**")
        st.write("Inject sudden heavy congestion factor on key network segments.")
        node_a = st.selectbox("From Stop:", [n.id for n in problem.nodes], format_func=lambda x: f"Node {x}: {problem.nodes[x].name}")
        node_b = st.selectbox("To Stop:", [n.id for n in problem.nodes if n.id != node_a], format_func=lambda x: f"Node {x}: {problem.nodes[x].name}")
        cong_multiplier = st.slider("Congestion Factor:", 2.0, 5.0, 3.0, 0.5)

        if st.button("⚠️ Apply Incident & Quantum Re-route"):
            if st.session_state.replanner is not None:
                with st.spinner("Re-optimizing around congested corridor..."):
                    up_prob, new_routes, res = st.session_state.replanner.inject_traffic_incident(
                        from_node=node_a,
                        to_node=node_b,
                        congestion_factor=cong_multiplier
                    )
                    st.session_state.problem = up_prob
                    st.session_state.optimization_results = res
                    st.warning(f"⚠️ Corridor Node {node_a} ↔ Node {node_b} congested ({cong_multiplier}x). Fleet re-routed.")
                    st.rerun()


# ----------------- TAB 6: SELF-TEST & DIAGNOSTICS -----------------
with tab6:
    st.markdown("### 🧪 **System Verification & 1-Click Diagnostics**")
    st.caption("Run automated test suites and verify quantum solver convergence directly inside the UI.")

    if st.button("▶️ Run Automated Test Suite (Pytest)"):
        with st.spinner("Running unit tests on QUBO, QAOA, VQE, and Hybrid Router..."):
            proc = subprocess.run(
                ["python", "-m", "pytest", "-v"],
                capture_output=True,
                text=True
            )
            if proc.returncode == 0:
                st.success("✅ All Unit Tests Passed Successfully!")
            else:
                st.error("⚠️ Test Failures Detected")
            st.code(proc.stdout + proc.stderr, language="text")

    st.divider()
    st.markdown("#### 📥 **Export Active Fleet Manifest**")
    fleet_rows = []
    for v in results["fleet_sustainability"]:
        route_names = " ➔ ".join(problem.nodes[i].name for i in v["route"])
        fleet_rows.append({
            "Vehicle ID": v["vehicle_id"],
            "Vehicle Name": v["vehicle_name"],
            "Powertrain Type": v["vehicle_type"],
            "Route Sequence": route_names,
            "Distance (km)": v["distance_km"],
            "Travel Time (min)": v["travel_time_min"],
            "Service Time (min)": v["service_time_min"],
            "Total Time (min)": v["total_time_min"],
            "Energy/Fuel": f"{v['fuel_consumed']} {v['fuel_unit']}",
            "CO2 Emissions (kg)": v["co2_emissions_kg"],
            "Operational Cost ($)": v["total_operational_cost"]
        })

    fleet_df = pd.DataFrame(fleet_rows)
    st.dataframe(fleet_df, use_container_width=True)

    csv_data = fleet_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Fleet Dispatch Manifest (CSV)",
        data=csv_data,
        file_name="quantex_fleet_dispatch.csv",
        mime="text/csv",
        type="primary"
    )
