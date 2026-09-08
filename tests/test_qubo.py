"""
Unit tests for QUBO formulation and Ising Hamiltonian translation.
"""

import numpy as np
import pytest
from quantex.core.qubo_formulator import QUBOFormulator


def test_qubo_generation_tsp():
    # 3-node graph (1 depot + 2 customer stops -> 4 binary variables with fix_depot=True)
    dist_matrix = np.array([
        [0.0, 10.0, 15.0],
        [10.0, 0.0, 8.0],
        [15.0, 8.0, 0.0]
    ])

    Q, offset, var_map = QUBOFormulator.build_tsp_qubo(dist_matrix, fix_depot=True)

    assert Q.shape == (4, 4), f"Expected shape (4, 4), got {Q.shape}"
    assert len(var_map) == 4

    # Convert to Ising Hamiltonian
    H_c, ising_offset = QUBOFormulator.get_sparse_pauli_op(Q, offset)
    assert H_c is not None
    assert H_c.num_qubits == 4


def test_bitstring_decoding():
    # 3 nodes: 0 (depot), 1, 2. (2*2 = 4 vars: x_1_1, x_1_2, x_2_1, x_2_2)
    # Target tour: 0 -> 1 -> 2 -> 0 => x_1_1 = 1, x_2_2 = 1, others 0 => bitstring "1001"
    b_str = "1001"
    route, is_valid = QUBOFormulator.decode_tsp_solution(b_str, num_nodes=3, fix_depot=True)
    assert route == [0, 1, 2, 0]
    assert is_valid is True
