# ⚡ QUANTEX: Quantum-Powered Fleet & Last-Mile Logistics Optimization Engine

> **Built for Centurion University of Technology and Management, Vizianagaram — Qiskit Fall Fest 2026 Hackathon (Day 02, Use Case 04: Last-Mile Delivery & Vehicle Routing)**

---

## 🌟 Overview

**Quantex** is an enterprise-ready, hybrid Quantum-Classical Vehicle Routing Engine designed to solve **combinatorially hard last-mile delivery, fleet scheduling, and dynamic routing problems**. By mapping the **Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)** to **Quadratic Unconstrained Binary Optimization (QUBO)** and **Ising Hamiltonians**, Quantex leverages **IBM Qiskit QAOA (Quantum Approximate Optimization Algorithm)**, **VQE (Variational Quantum Eigensolver)**, and **Transverse-Field Quantum-Inspired Simulated Annealing (QISA)** to deliver:

- 🌿 **Lower Carbon ($CO_2$) Emissions** across heterogeneous fleets (EVs, Diesel Vans, Gas Trucks).
- ⛽ **Reduced Fuel & Energy Consumption**.
- ⏱️ **Faster Turnaround Times & Traffic Resiliency** with real-time on-the-fly quantum re-routing.
- 💰 **Measurable Financial Cost Savings**.

---

## 🚀 Key Features

1. **Exact Quantum Mathematical Modeling**:
   - Formulation of TSP and Multi-Vehicle CVRP into QUBO cost functions and Ising Hamiltonians ($\hat{H}_C$).
   - Variable reduction: Fixes depot index to reduce required qubits from $N^2$ to $(N-1)^2$.
   - Quadratic penalty multipliers for degree, cycle-integrity, and vehicle payload capacity constraints.
2. **Qiskit-Native Quantum Solvers**:
   - **QAOA Solver**: Parameterized ansatz with configurable $p$-depth layers, cost evolution ($e^{-i\gamma \hat{H}_C}$), and transverse-field mixer ($e^{-i\beta \hat{H}_M}$) optimized via classical minimizers (`COBYLA`, `SLSQP`).
   - **VQE Solver**: Variational Quantum Eigensolver utilizing `TwoLocal` and `RealAmplitudes` ansatzes.
   - **Quantum-Inspired Simulated Annealing (QISA)**: Transverse-field quantum tunneling simulation for scaling to massive distribution networks ($N > 15$).
3. **Hybrid Quantum-Classical Architecture**:
   - Capacity-aware K-Means clustering partitions large delivery regions into optimal vehicle payloads.
   - Quantum solvers optimize each sub-tour Hamiltonian.
4. **Dynamic Logistics Event Re-planner**:
   - Live injection of urgent emergency orders & real-time road congestion spikes with instant quantum re-optimization.
5. **Interactive Streamlit Web Dashboard**:
   - **Interactive Map**: Folium/Leaflet visualization with route paths, customer demands, time-windows, and depot waypoints.
   - **Quantum Circuit Visualizer**: Circuit depth, gate counts, CNOT entanglement analysis, parameter tracking, and ASCII schematics.
   - **Statevector Telemetry**: Probability distribution histogram of computational basis states.
   - **Solver Arena**: Live benchmarking comparing Classical Greedy (Nearest Neighbor), 2-Opt, QAOA, VQE, and QISA.
   - **Dispatch Manifest Export**: One-click CSV export of route schedules and ESG sustainability metrics.

---

## 📦 Project Architecture

```
Quantex/
├── quantex/
│   ├── core/
│   │   ├── problem_model.py       # Graph representation, dynamic traffic, time-windows, vehicles
│   │   ├── qubo_formulator.py     # Mathematical TSP/VRP to QUBO & Qiskit SparsePauliOp
│   │   └── emissions.py           # Green logistics engine (fuel, CO2, cost savings)
│   ├── quantum/
│   │   ├── circuit_builder.py     # Parameterized QAOA/VQE circuits & telemetry extractor
│   │   ├── qaoa_solver.py         # Qiskit QAOA execution & statevector sampler
│   │   ├── vqe_solver.py          # Qiskit VQE ground state eigensolver
│   │   └── quantum_inspired.py    # Transverse-field simulated quantum annealing (QISA)
│   ├── hybrid/
│   │   ├── cluster_router.py      # Hybrid Classical Clustering + Sub-problem Quantum Routing
│   │   └── dynamic_replanner.py   # Real-time incident and emergency order re-planner
│   ├── classical/
│   │   └── classical_solvers.py   # Exact DP, Nearest Neighbor, 2-Opt baselines
│   └── data/
│       └── presets.py             # E-Commerce, Postal, Field Services, Municipal presets
│
├── app.py                         # Interactive Streamlit Web Application
├── run_cli.py                     # CLI Benchmark & Simulation Tool
├── tests/                         # Automated test suite (pytest)
└── requirements.txt               # Dependencies
```

---

## 🛠️ Installation & Setup

1. **Clone or Navigate to the Repository**:
   ```bash
   cd Quantex
   ```

2. **Install Dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Run Automated Test Suite**:
   ```bash
   python -m pytest -v
   ```

---

## 🖥️ Running Locally (FastAPI + Custom 3D Animated UI)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

---

## ☁️ Deploying to Render (1-Click Ready)

Quantex is pre-configured with `Procfile` and `render.yaml` for zero-configuration deployment on **Render**:

### Steps to Deploy on Render:
1. Push your `Quantex` repository to GitHub or GitLab.
2. Log into [Render.com](https://render.com) and click **New +** ➔ **Web Service**.
3. Select your repository.
4. Render will automatically detect `render.yaml` and `Procfile`.
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service** and your quantum platform is live!

---

## 📐 Mathematical Formulation

### 1. QUBO Formulation for TSP / Sub-Route
Given distance matrix $d_{ij}$ and binary variables $x_{i, p} \in \{0, 1\}$ indicating node $i$ visited at step $p$:

$$\min \sum_{u} \sum_{v} \sum_{p} d_{uv} x_{u, p} x_{v, (p+1)} + A \sum_{p} \left( \sum_{i} x_{i, p} - 1 \right)^2 + A \sum_{i} \left( \sum_{p} x_{i, p} - 1 \right)^2$$

### 2. Ising Hamiltonian Transformation
Mapping binary variables $x_i \to \frac{I - Z_i}{2}$:

$$\hat{H}_C = \sum_{i} h_i Z_i + \sum_{i < j} J_{ij} Z_i Z_j + \text{offset} \cdot I$$

### 3. QAOA State Evolution
$$|\psi(\vec{\gamma}, \vec{\beta})\rangle = \prod_{l=1}^p e^{-i \beta_l \hat{H}_M} e^{-i \gamma_l \hat{H}_C} |+\rangle^{\otimes n}$$
where the mixer Hamiltonian is $\hat{H}_M = \sum_{i=1}^n X_i$.

---

## 🏆 Hackathon Use Cases Supported

- **E-Commerce Express Delivery**: High-density urban parcel distribution with time-window constraints.
- **Postal & Courier Dispatch**: Regional sorting hub to neighborhood locker boxes and branch offices.
- **Field Services & Maintenance**: Urgent emergency repair dispatch with technician service durations.
- **Municipal Waste & Recyclables Collection**: Heavy compactor truck scheduling with bin fill capacities.

---

## 📄 License & Attribution
Developed with ❤️ for **Centurion University of Technology and Management & Qiskit Fall Fest 2026**.
Powered by **IBM Qiskit**, **Python**, and **Streamlit**.
