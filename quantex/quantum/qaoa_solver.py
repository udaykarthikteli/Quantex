"""
Quantum Approximate Optimization Algorithm (QAOA) Solver for Routing Problems.
Implements parameter optimization, statevector/sampling execution, and solution decoding.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import time
from scipy.optimize import minimize

try:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector, SparsePauliOp
    from quantex.quantum.circuit_builder import QuantumCircuitBuilder
    from quantex.core.qubo_formulator import QUBOFormulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


class QAOASolver:
    """
    QAOA solver utilizing Qiskit Quantum Circuits and Scipy classical optimizers.
    """

    def __init__(
        self,
        reps: int = 1,
        optimizer_name: str = "COBYLA",
        max_iter: int = 25,
        shots: int = 1024,
        seed: int = 42
    ):
        self.reps = reps
        self.optimizer_name = optimizer_name
        self.max_iter = max_iter
        self.shots = shots
        self.seed = seed

    def solve(
        self,
        cost_hamiltonian: SparsePauliOp,
        offset: float = 0.0,
        num_nodes: int = 4,
        fix_depot: bool = True,
        initial_point: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Executes QAOA on the given cost Hamiltonian.
        
        Returns:
            optimal_route: Best decoded node sequence
            optimal_bitstring: Binary bitstring corresponding to the minimum cost state
            optimal_cost: Energy expectation / objective value
            runtime_sec: Total solver execution time
            circuit: The generated QuantumCircuit
            convergence: Optimization cost trajectory
            state_probabilities: Sampled probabilities of top states
        """
        start_time = time.time()
        num_qubits = cost_hamiltonian.num_qubits

        # Build parameterized QAOA circuit without measurement for statevector simulation
        qc = QuantumCircuitBuilder.build_qaoa_circuit(
            cost_hamiltonian=cost_hamiltonian,
            reps=self.reps,
            mixer_type="standard_x"
        )
        # Remove measurement for expectation evaluation
        qc_no_meas = qc.remove_final_measurements(inplace=False)

        # Optimization history tracking
        history_evals = []
        history_costs = []

        def cost_objective(params: np.ndarray) -> float:
            # Bind parameters: gammas first, then betas
            bound_qc = qc_no_meas.assign_parameters(params)
            sv = Statevector.from_instruction(bound_qc)
            # Expectation value: <psi | H_c | psi> + offset
            exp_val = float(np.real(sv.expectation_value(cost_hamiltonian))) + offset
            history_evals.append(len(history_evals) + 1)
            history_costs.append(exp_val)
            return exp_val

        # Initial parameter point: gammas in [0, pi], betas in [0, pi/2]
        if initial_point is None:
            rng = np.random.RandomState(self.seed)
            init_gammas = rng.uniform(0.1, np.pi * 0.8, self.reps)
            init_betas = rng.uniform(0.1, np.pi * 0.4, self.reps)
            initial_point = np.concatenate([init_gammas, init_betas])

        # Classical optimization
        opt_res = minimize(
            fun=cost_objective,
            x0=initial_point,
            method=self.optimizer_name,
            options={"maxiter": self.max_iter}
        )

        optimal_params = opt_res.x
        optimal_energy = float(opt_res.fun)

        # Sample final statevector with optimal parameters
        final_qc = qc_no_meas.assign_parameters(optimal_params)
        final_sv = Statevector.from_instruction(final_qc)
        probs = final_sv.probabilities_dict()

        # Sort bitstrings by probability descending
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        top_states = sorted_probs[:16]

        # In Qiskit, bitstrings from statevector are little-endian (qubit N-1 on left).
        # We need standard left-to-right indexing matching our QUBO variable layout.
        best_bitstring = None
        best_route = None
        best_route_valid = False
        min_classical_cost = float("inf")

        state_distribution = {}
        for b_str, prob in top_states:
            # Reverse bitstring to match QUBO variable order: qubit 0 is index 0
            ordered_b = b_str[::-1]
            state_distribution[ordered_b] = round(float(prob), 5)
            
            route, is_valid = QUBOFormulator.decode_tsp_solution(
                ordered_b, num_nodes=num_nodes, fix_depot=fix_depot
            )
            if best_bitstring is None:
                best_bitstring = ordered_b
                best_route = route
                best_route_valid = is_valid

            if is_valid and not best_route_valid:
                best_bitstring = ordered_b
                best_route = route
                best_route_valid = True

        runtime = time.time() - start_time

        return {
            "solver": f"Qiskit QAOA (p={self.reps}, {self.optimizer_name})",
            "optimal_bitstring": best_bitstring,
            "optimal_route": best_route,
            "is_valid_route": best_route_valid,
            "optimal_energy": round(optimal_energy, 4),
            "runtime_sec": round(runtime, 4),
            "num_qubits": num_qubits,
            "optimal_params": optimal_params.tolist(),
            "convergence": list(zip(history_evals, history_costs)),
            "state_distribution": state_distribution,
            "circuit": qc
        }
