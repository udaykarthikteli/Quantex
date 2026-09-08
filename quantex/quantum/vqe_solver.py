"""
Variational Quantum Eigensolver (VQE) for Routing Problems.
Finds minimum eigenvalue and corresponding ground state bitstring using parameterized ansatz.
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


class VQESolver:
    """
    VQE solver using parameterizable Ry-Rz / RealAmplitudes ansatz.
    """

    def __init__(
        self,
        ansatz_type: str = "two_local",
        reps: int = 2,
        optimizer_name: str = "COBYLA",
        max_iter: int = 100,
        seed: int = 42
    ):
        self.ansatz_type = ansatz_type
        self.reps = reps
        self.optimizer_name = optimizer_name
        self.max_iter = max_iter
        self.seed = seed

    def solve(
        self,
        cost_hamiltonian: SparsePauliOp,
        offset: float = 0.0,
        num_nodes: int = 4,
        fix_depot: bool = True
    ) -> Dict[str, Any]:
        """
        Executes VQE to find minimum energy state.
        """
        start_time = time.time()
        num_qubits = cost_hamiltonian.num_qubits

        ansatz = QuantumCircuitBuilder.build_vqe_ansatz(
            num_qubits=num_qubits,
            ansatz_type=self.ansatz_type,
            reps=self.reps
        )

        history_evals = []
        history_costs = []

        def cost_objective(params: np.ndarray) -> float:
            bound_qc = ansatz.assign_parameters(params)
            sv = Statevector.from_instruction(bound_qc)
            exp_val = float(np.real(sv.expectation_value(cost_hamiltonian))) + offset
            history_evals.append(len(history_evals) + 1)
            history_costs.append(exp_val)
            return exp_val

        rng = np.random.RandomState(self.seed)
        initial_point = rng.uniform(-np.pi, np.pi, ansatz.num_parameters)

        opt_res = minimize(
            fun=cost_objective,
            x0=initial_point,
            method=self.optimizer_name,
            options={"maxiter": self.max_iter}
        )

        optimal_params = opt_res.x
        optimal_energy = float(opt_res.fun)

        # Sample final statevector
        final_qc = ansatz.assign_parameters(optimal_params)
        final_sv = Statevector.from_instruction(final_qc)
        probs = final_sv.probabilities_dict()

        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        top_states = sorted_probs[:16]

        best_bitstring = None
        best_route = None
        best_route_valid = False

        state_distribution = {}
        for b_str, prob in top_states:
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
            "solver": f"Qiskit VQE ({self.ansatz_type}, reps={self.reps}, {self.optimizer_name})",
            "optimal_bitstring": best_bitstring,
            "optimal_route": best_route,
            "is_valid_route": best_route_valid,
            "optimal_energy": round(optimal_energy, 4),
            "runtime_sec": round(runtime, 4),
            "num_qubits": num_qubits,
            "optimal_params": optimal_params.tolist(),
            "convergence": list(zip(history_evals, history_costs)),
            "state_distribution": state_distribution,
            "circuit": ansatz
        }
