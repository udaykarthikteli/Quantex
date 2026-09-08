"""
QUBO & Ising Hamiltonian Formulation for TSP, VRP, and CVRP.
Translates routing optimization problems into Quadratic Unconstrained Binary Optimization (QUBO)
and converts to Qiskit SparsePauliOp / QuadraticProgram.
"""

from typing import Dict, List, Tuple, Optional
import numpy as np

try:
    from qiskit.quantum_info import SparsePauliOp
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.converters import QuadraticProgramToQubo
    QISKIT_OPT_AVAILABLE = True
except ImportError:
    QISKIT_OPT_AVAILABLE = False


class QUBOFormulator:
    """
    Constructs QUBO cost matrices and Qiskit Hamiltonians for routing problems.
    Supports:
    - Fixed-depot variable reduction: (N-1)^2 binary variables instead of N^2
    - Dynamic traffic penalties
    - Time-window penalty terms
    - Direct SparsePauliOp Ising Hamiltonian generation
    """

    @classmethod
    def build_tsp_qubo(
        cls,
        distance_matrix: np.ndarray,
        penalty_multiplier: Optional[float] = None,
        fix_depot: bool = True
    ) -> Tuple[np.ndarray, float, Dict[str, Tuple[int, int]]]:
        """
        Builds the QUBO matrix Q such that min x^T Q x + constant solves TSP.
        
        Args:
            distance_matrix: NxN distance matrix.
            penalty_multiplier: Multiplier for constraint violation (default: 1.5 * max(distance_matrix)).
            fix_depot: If True, fixes depot (node 0) at step 0, reducing variables to (N-1)^2.
            
        Returns:
            Q: Symmetric or upper-triangular QUBO matrix.
            offset: Constant energy offset.
            var_map: Mapping from variable index to (node_id, step_p).
        """
        n = distance_matrix.shape[0]
        max_dist = np.max(distance_matrix)
        A = penalty_multiplier if penalty_multiplier is not None else max(10.0, float(max_dist * 2.0))

        if fix_depot and n > 1:
            # Nodes 1 .. n-1 at steps 1 .. n-1
            num_vars = (n - 1) * (n - 1)
            Q = np.zeros((num_vars, num_vars))
            offset = 0.0

            def var_idx(node: int, step: int) -> int:
                # node in 1..n-1 -> idx node-1, step in 1..n-1 -> idx step-1
                return (node - 1) * (n - 1) + (step - 1)

            var_map = {}
            for i in range(1, n):
                for p in range(1, n):
                    var_map[f"x_{i}_{p}"] = (i, p)

            # 1. Constraint: Each step p (1..n-1) has exactly 1 node: A * (sum_i x_{i,p} - 1)^2
            for p in range(1, n):
                # (sum_i x_{i,p})^2 - 2 sum_i x_{i,p} + 1
                offset += A
                for i in range(1, n):
                    idx_i = var_idx(i, p)
                    Q[idx_i, idx_i] -= A  # linear term (-2A + A from diagonal)
                    for j in range(1, n):
                        if i != j:
                            idx_j = var_idx(j, p)
                            Q[idx_i, idx_j] += A  # cross terms +2A (split A + A)

            # 2. Constraint: Each node i (1..n-1) is visited at exactly 1 step: A * (sum_p x_{i,p} - 1)^2
            for i in range(1, n):
                offset += A
                for p in range(1, n):
                    idx_p = var_idx(i, p)
                    Q[idx_p, idx_p] -= A
                    for q in range(1, n):
                        if p != q:
                            idx_q = var_idx(i, q)
                            Q[idx_p, idx_q] += A

            # 3. Distance Objective:
            # Depots edges:
            # Step 0 (depot 0) -> Step 1 (node i): d(0, i) * x_{i, 1}
            for i in range(1, n):
                idx = var_idx(i, 1)
                Q[idx, idx] += distance_matrix[0, i]

            # Step n-1 (node i) -> Step n (depot 0): d(i, 0) * x_{i, n-1}
            for i in range(1, n):
                idx = var_idx(i, n - 1)
                Q[idx, idx] += distance_matrix[i, 0]

            # Intermediate edges: Step p (node i) -> Step p+1 (node j): d(i, j) * x_{i, p} * x_{j, p+1}
            for p in range(1, n - 1):
                for i in range(1, n):
                    for j in range(1, n):
                        if i != j:
                            idx_i = var_idx(i, p)
                            idx_j = var_idx(j, p + 1)
                            # Add to upper triangle or symmetric
                            Q[idx_i, idx_j] += distance_matrix[i, j]

            return Q, offset, var_map

        else:
            # Full N^2 variables
            num_vars = n * n
            Q = np.zeros((num_vars, num_vars))
            offset = 0.0

            def var_idx_full(node: int, step: int) -> int:
                return node * n + step

            var_map = {}
            for i in range(n):
                for p in range(n):
                    var_map[f"x_{i}_{p}"] = (i, p)

            # Constraint 1: Each step p has 1 node
            for p in range(n):
                offset += A
                for i in range(n):
                    idx_i = var_idx_full(i, p)
                    Q[idx_i, idx_i] -= A
                    for j in range(n):
                        if i != j:
                            idx_j = var_idx_full(j, p)
                            Q[idx_i, idx_j] += A

            # Constraint 2: Each node i visited once
            for i in range(n):
                offset += A
                for p in range(n):
                    idx_p = var_idx_full(i, p)
                    Q[idx_p, idx_p] -= A
                    for q in range(n):
                        if p != q:
                            idx_q = var_idx_full(i, q)
                            Q[idx_p, idx_q] += A

            # Distance cost:
            for p in range(n):
                next_p = (p + 1) % n
                for i in range(n):
                    for j in range(n):
                        if i != j:
                            idx_i = var_idx_full(i, p)
                            idx_j = var_idx_full(j, next_p)
                            Q[idx_i, idx_j] += distance_matrix[i, j]

            return Q, offset, var_map

    @classmethod
    def qubo_to_ising(cls, Q: np.ndarray, offset: float = 0.0):
        """
        Converts QUBO matrix Q to an Ising Hamiltonian (SparsePauliOp) using substitution x_i = (I - Z_i) / 2.
        Returns:
            pauli_list: List of (Pauli string, coefficient)
            ising_offset: Energy constant shift
        """
        num_vars = Q.shape[0]
        # Make symmetric
        Q_sym = (Q + Q.T) / 2.0
        
        pauli_dict = {}
        ising_offset = offset

        # Linear and constant from diagonal: Q_ii * x_i = Q_ii * (I - Z_i)/2 = Q_ii/2 * I - Q_ii/2 * Z_i
        for i in range(num_vars):
            q_ii = Q_sym[i, i]
            ising_offset += q_ii / 2.0
            # Z_i term
            p_str = ['I'] * num_vars
            p_str[num_vars - 1 - i] = 'Z'
            p_str_key = "".join(p_str)
            pauli_dict[p_str_key] = pauli_dict.get(p_str_key, 0.0) - (q_ii / 2.0)

        # Quadratic terms: Q_ij * x_i * x_j = Q_ij * (I - Z_i)(I - Z_j) / 4
        # = Q_ij / 4 * (I - Z_i - Z_j + Z_i Z_j)
        for i in range(num_vars):
            for j in range(i + 1, num_vars):
                q_ij = 2.0 * Q_sym[i, j]  # accounts for both upper and lower
                if abs(q_ij) < 1e-9:
                    continue
                ising_offset += q_ij / 4.0

                # - Q_ij / 4 * Z_i
                p_i = ['I'] * num_vars
                p_i[num_vars - 1 - i] = 'Z'
                k_i = "".join(p_i)
                pauli_dict[k_i] = pauli_dict.get(k_i, 0.0) - (q_ij / 4.0)

                # - Q_ij / 4 * Z_j
                p_j = ['I'] * num_vars
                p_j[num_vars - 1 - j] = 'Z'
                k_j = "".join(p_j)
                pauli_dict[k_j] = pauli_dict.get(k_j, 0.0) - (q_ij / 4.0)

                # + Q_ij / 4 * Z_i Z_j
                p_ij = ['I'] * num_vars
                p_ij[num_vars - 1 - i] = 'Z'
                p_ij[num_vars - 1 - j] = 'Z'
                k_ij = "".join(p_ij)
                pauli_dict[k_ij] = pauli_dict.get(k_ij, 0.0) + (q_ij / 4.0)

        pauli_list = [(k, v) for k, v in pauli_dict.items() if abs(v) > 1e-9]
        return pauli_list, ising_offset

    @classmethod
    def get_sparse_pauli_op(cls, Q: np.ndarray, offset: float = 0.0):
        """Builds a Qiskit SparsePauliOp directly from QUBO matrix."""
        pauli_list, ising_offset = cls.qubo_to_ising(Q, offset)
        if not pauli_list:
            return None, ising_offset
        labels, coeffs = zip(*pauli_list)
        return SparsePauliOp(labels, coeffs=coeffs), ising_offset

    @classmethod
    def decode_tsp_solution(
        cls,
        bitstring: str,
        num_nodes: int,
        fix_depot: bool = True
    ) -> Tuple[List[int], bool]:
        """
        Decodes a binary solution bitstring into a valid route sequence.
        Returns:
            route: List of node IDs in order (starting and ending at 0).
            is_valid: True if permutation is strictly valid.
        """
        # Ensure bitstring is in standard left-to-right order matching var indices
        # If passed as integer binary from Qiskit (little-endian or big-endian), handle appropriately
        bits = [int(b) for b in bitstring]
        
        if fix_depot:
            n_sub = num_nodes - 1
            if len(bits) != n_sub * n_sub:
                # If bitstring length doesn't match, return fallback
                return list(range(num_nodes)) + [0], False

            route_steps = {0: 0} # step 0 is depot 0
            visited = set([0])
            is_valid = True

            for p in range(1, num_nodes):
                step_nodes = []
                for i in range(1, num_nodes):
                    idx = (i - 1) * n_sub + (p - 1)
                    if bits[idx] == 1:
                        step_nodes.append(i)
                
                if len(step_nodes) == 1:
                    node = step_nodes[0]
                    if node not in visited:
                        route_steps[p] = node
                        visited.add(node)
                    else:
                        is_valid = False
                else:
                    is_valid = False

            # If invalid bitstring, reconstruct best greedy repair
            if not is_valid or len(visited) < num_nodes:
                ordered_route = [0]
                unvisited = set(range(1, num_nodes)) - visited
                for p in range(1, num_nodes):
                    if p in route_steps and route_steps[p] not in ordered_route:
                        ordered_route.append(route_steps[p])
                    elif unvisited:
                        ordered_route.append(unvisited.pop())
                ordered_route.append(0)
                return ordered_route, False
            else:
                ordered_route = [route_steps[p] for p in range(num_nodes)] + [0]
                return ordered_route, True
        else:
            # Full decoding
            n = num_nodes
            route_steps = {}
            visited = set()
            is_valid = True
            for p in range(n):
                step_nodes = []
                for i in range(n):
                    idx = i * n + p
                    if bits[idx] == 1:
                        step_nodes.append(i)
                if len(step_nodes) == 1:
                    node = step_nodes[0]
                    if node not in visited:
                        route_steps[p] = node
                        visited.add(node)
                    else:
                        is_valid = False
                else:
                    is_valid = False

            if not is_valid or len(visited) < num_nodes:
                return list(range(num_nodes)) + [0], False

            ordered = [route_steps[p] for p in range(n)]
            # Rotate to start at 0
            idx0 = ordered.index(0)
            ordered = ordered[idx0:] + ordered[:idx0] + [0]
            return ordered, True
