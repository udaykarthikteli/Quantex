"""
Quantum Circuit Builder and Visualizer for QAOA and VQE Routing Circuits.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit import ParameterVector
    from qiskit.circuit.library import TwoLocal, RealAmplitudes
    from qiskit.quantum_info import SparsePauliOp
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


class QuantumCircuitBuilder:
    """
    Constructs parameterized quantum circuits for QAOA and VQE,
    and extracts circuit metrics (gate counts, depth, qubit count).
    """

    @classmethod
    def build_qaoa_circuit(
        cls,
        cost_hamiltonian: SparsePauliOp,
        reps: int = 1,
        mixer_type: str = "standard_x"
    ) -> QuantumCircuit:
        """
        Builds a QAOA parameterized QuantumCircuit.
        
        Args:
            cost_hamiltonian: SparsePauliOp encoding QUBO cost.
            reps: Number of QAOA layers (depth p).
            mixer_type: 'standard_x' (all-qubit Rx) or 'xy_ring' (parity-preserving XY).
        """
        num_qubits = cost_hamiltonian.num_qubits
        qc = QuantumCircuit(num_qubits)

        # Initial state: equal superposition |+>^n
        qc.h(range(num_qubits))
        qc.barrier(label="Init |+>")

        # Parameter vectors
        gammas = ParameterVector("γ", reps)
        betas = ParameterVector("β", reps)

        for p in range(reps):
            # Cost Hamiltonian layer: e^{-i γ H_C}
            for pauli, coeff in zip(cost_hamiltonian.paulis, cost_hamiltonian.coeffs):
                weight = float(np.real(coeff))
                if abs(weight) < 1e-9:
                    continue

                pauli_str = pauli.to_label()
                z_indices = [num_qubits - 1 - i for i, ch in enumerate(pauli_str) if ch == 'Z']

                if len(z_indices) == 1:
                    # Single qubit Rz(2 * weight * gamma)
                    qc.rz(2.0 * weight * gammas[p], z_indices[0])
                elif len(z_indices) == 2:
                    # Two qubit ZZ interaction: CNOT -> Rz(2 * weight * gamma) -> CNOT
                    q1, q2 = z_indices[0], z_indices[1]
                    qc.cx(q1, q2)
                    qc.rz(2.0 * weight * gammas[p], q2)
                    qc.cx(q1, q2)

            qc.barrier(label=f"Cost Layer {p+1}")

            # Mixer Hamiltonian layer: e^{-i β H_M}
            if mixer_type == "standard_x":
                for q in range(num_qubits):
                    qc.rx(2.0 * betas[p], q)
            elif mixer_type == "xy_ring":
                # Ring mixer preserving Hamming weight
                for q in range(num_qubits):
                    q_next = (q + 1) % num_qubits
                    qc.rxx(2.0 * betas[p], q, q_next)
                    qc.ryy(2.0 * betas[p], q, q_next)

            qc.barrier(label=f"Mixer Layer {p+1}")

        qc.measure_all()
        return qc

    @classmethod
    def build_vqe_ansatz(
        cls,
        num_qubits: int,
        ansatz_type: str = "two_local",
        reps: int = 2
    ) -> QuantumCircuit:
        """
        Builds a variational ansatz for VQE.
        """
        try:
            from qiskit.circuit.library import two_local, real_amplitudes
            if ansatz_type == "real_amplitudes":
                return real_amplitudes(num_qubits=num_qubits, reps=reps, entanglement="linear")
            else:
                return two_local(
                    num_qubits=num_qubits,
                    rotation_blocks=["ry", "rz"],
                    entanglement_blocks="cx",
                    entanglement="linear",
                    reps=reps
                )
        except (ImportError, AttributeError):
            if ansatz_type == "real_amplitudes":
                ansatz = RealAmplitudes(num_qubits=num_qubits, reps=reps, entanglement="linear")
            else:
                ansatz = TwoLocal(
                    num_qubits=num_qubits,
                    rotation_blocks=["ry", "rz"],
                    entanglement_blocks="cx",
                    entanglement="linear",
                    reps=reps
                )
            return ansatz

    @classmethod
    def get_circuit_telemetry(cls, qc: QuantumCircuit) -> Dict[str, Any]:
        """
        Extracts structural telemetry from a QuantumCircuit.
        """
        gate_counts = dict(qc.count_ops())
        return {
            "num_qubits": qc.num_qubits,
            "depth": qc.depth(),
            "num_gates": sum(gate_counts.values()),
            "cnot_count": gate_counts.get("cx", 0),
            "single_qubit_gates": sum(v for k, v in gate_counts.items() if k not in ["cx", "cz", "barrier", "measure"]),
            "num_parameters": qc.num_parameters,
            "gate_breakdown": gate_counts
        }

    @classmethod
    def draw_circuit_ascii(cls, qc: QuantumCircuit) -> str:
        """Renders circuit to formatted ASCII text."""
        return qc.draw(output="text", fold=100)
