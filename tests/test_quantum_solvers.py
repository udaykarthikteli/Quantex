"""
Unit tests for Qiskit QAOA, VQE, and Quantum-Inspired Solvers.
"""

import numpy as np
import pytest
from quantex.core.qubo_formulator import QUBOFormulator
from quantex.quantum.qaoa_solver import QAOASolver
from quantex.quantum.vqe_solver import VQESolver
from quantex.quantum.quantum_inspired import QuantumInspiredSolver
from quantex.classical.classical_solvers import ClassicalSolvers


@pytest.fixture
def sample_tsp_instance():
    dist_matrix = np.array([
        [0.0, 5.0, 12.0],
        [5.0, 0.0, 7.0],
        [12.0, 7.0, 0.0]
    ])
    Q, offset, _ = QUBOFormulator.build_tsp_qubo(dist_matrix, fix_depot=True)
    H_c, ising_offset = QUBOFormulator.get_sparse_pauli_op(Q, offset)
    return dist_matrix, Q, offset, H_c, ising_offset


def test_qaoa_solver(sample_tsp_instance):
    dist_matrix, Q, offset, H_c, ising_offset = sample_tsp_instance
    solver = QAOASolver(reps=1, max_iter=20)
    res = solver.solve(H_c, offset=ising_offset, num_nodes=3, fix_depot=True)

    assert "optimal_route" in res
    assert len(res["optimal_route"]) == 4
    assert res["optimal_route"][0] == 0
    assert res["optimal_route"][-1] == 0
    assert res["num_qubits"] == 4


def test_vqe_solver(sample_tsp_instance):
    dist_matrix, Q, offset, H_c, ising_offset = sample_tsp_instance
    solver = VQESolver(reps=1, max_iter=20)
    res = solver.solve(H_c, offset=ising_offset, num_nodes=3, fix_depot=True)

    assert "optimal_route" in res
    assert len(res["optimal_route"]) == 4
    assert res["optimal_route"][0] == 0


def test_quantum_inspired_solver(sample_tsp_instance):
    dist_matrix, Q, offset, _, _ = sample_tsp_instance
    qisa = QuantumInspiredSolver(num_sweeps=100)
    res = qisa.solve(Q, offset=offset, num_nodes=3)

    assert res["bitstring"] is not None
    route, _ = QUBOFormulator.decode_tsp_solution(res["bitstring"], num_nodes=3, fix_depot=True)
    assert len(route) == 4
    assert route[0] == 0
