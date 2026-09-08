"""
Quantum-Inspired Simulated Annealing (QISA) & Transverse-Field Ising Solver.
Leverages quantum tunneling simulation for scalable fleet routing (N > 15).
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
import time


class QuantumInspiredSolver:
    """
    Simulates quantum annealing dynamics with transverse field tunneling
    over the QUBO/Ising cost landscape.
    """

    def __init__(
        self,
        num_trotters: int = 8,
        gamma_init: float = 2.5,
        gamma_final: float = 0.01,
        temperature_init: float = 5.0,
        temperature_final: float = 0.01,
        num_sweeps: int = 600,
        seed: Optional[int] = 42
    ):
        self.num_trotters = num_trotters
        self.gamma_init = gamma_init
        self.gamma_final = gamma_final
        self.temperature_init = temperature_init
        self.temperature_final = temperature_final
        self.num_sweeps = num_sweeps
        self.rng = np.random.RandomState(seed)

    def solve(
        self,
        Q: np.ndarray,
        offset: float = 0.0,
        num_nodes: int = 4
    ) -> Dict[str, any]:
        """
        Executes Simulated Quantum Annealing (SQA) on the QUBO matrix.
        
        Returns:
            best_bitstring: Binary array of shape (num_vars,)
            best_energy: Minimum energy found
            convergence_history: Energy vs sweep index
            runtime_sec: Execution time
        """
        start_time = time.time()
        num_vars = Q.shape[0]

        # Symmetrize QUBO
        Q_sym = (Q + Q.T) / 2.0

        # Initialize trotter replicas: spins in {-1, +1}
        spins = self.rng.choice([-1, 1], size=(self.num_trotters, num_vars))

        best_energy = float("inf")
        best_bitstring = None
        convergence_history = []

        for sweep in range(self.num_sweeps):
            # Annealing schedules
            progress = sweep / float(max(1, self.num_sweeps - 1))
            gamma = self.gamma_init * (1.0 - progress) + self.gamma_final * progress
            temp = self.temperature_init * (1.0 - progress) + self.temperature_final * progress
            beta = 1.0 / max(1e-4, temp)
            
            # Quantum coupling between Trotter slices
            J_perp = -0.5 * temp * np.log(np.tanh(max(1e-4, gamma / (self.num_trotters * temp))))

            for m in range(self.num_trotters):
                m_prev = (m - 1) % self.num_trotters
                m_next = (m + 1) % self.num_trotters

                # Update each spin variable
                for i in range(num_vars):
                    s_i = spins[m, i]
                    # Convert to binary x in {0, 1}
                    # delta energy for spin flip: s_i -> -s_i (x_i -> 1 - x_i)
                    x_current = (1 - spins[m, :]) / 2.0  # +1 -> 0, -1 -> 1
                    
                    # Local field from QUBO
                    local_field = Q_sym[i, i] + np.sum(Q_sym[i, :] * x_current) - Q_sym[i, i] * x_current[i]
                    # Change in QUBO objective if x_i is toggled:
                    if x_current[i] == 0:
                        # 0 -> 1
                        delta_H_classical = Q_sym[i, i] + np.sum(Q_sym[i, :] * x_current)
                    else:
                        # 1 -> 0
                        delta_H_classical = -Q_sym[i, i] - np.sum(Q_sym[i, :] * (x_current)) + Q_sym[i, i]

                    # Quantum Trotter coupling term
                    delta_H_quantum = -2.0 * J_perp * s_i * (spins[m_prev, i] + spins[m_next, i])

                    delta_total = (delta_H_classical / self.num_trotters) + delta_H_quantum

                    # Metropolis acceptance with quantum tunneling
                    if delta_total < 0 or self.rng.rand() < np.exp(-delta_total * beta):
                        spins[m, i] = -s_i

            # Check best configuration across trotters
            for m in range(self.num_trotters):
                x_cand = ((1 - spins[m, :]) / 2.0).astype(int)
                energy = float(x_cand.T @ Q_sym @ x_cand + offset)
                if energy < best_energy:
                    best_energy = energy
                    best_bitstring = "".join(str(b) for b in x_cand)

            if sweep % max(1, self.num_sweeps // 50) == 0:
                convergence_history.append((sweep, best_energy))

        runtime = time.time() - start_time
        return {
            "bitstring": best_bitstring,
            "energy": best_energy,
            "convergence": convergence_history,
            "runtime_sec": round(runtime, 4),
            "solver": "Quantum-Inspired Simulated Annealing (QISA)"
        }
