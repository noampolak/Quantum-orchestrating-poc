"""Unit tests for quantum execution logic."""

import pytest
from qiskit import QuantumCircuit

from app.quantum.execution import parse_qasm3, execute_circuit, NUM_SHOTS


def test_parse_qasm3_valid(sample_qasm3):
    """Test parsing valid QASM3 string."""
    circuit = parse_qasm3(sample_qasm3)

    assert isinstance(circuit, QuantumCircuit)
    assert circuit.num_qubits == 2


def test_parse_qasm3_invalid():
    """Test parsing invalid QASM3 string."""
    invalid_qasm3 = "INVALID QASM3 STRING"

    with pytest.raises(ValueError, match="Invalid QASM3"):
        parse_qasm3(invalid_qasm3)


def test_parse_qasm3_empty():
    """Test parsing empty QASM3 string."""
    with pytest.raises(ValueError):
        parse_qasm3("")


def test_execute_circuit(sample_qasm3):
    """Test executing a quantum circuit."""
    circuit = parse_qasm3(sample_qasm3)
    counts = execute_circuit(circuit)

    assert isinstance(counts, dict)
    assert len(counts) > 0
    # Check that all values are integers (counts)
    assert all(isinstance(v, int) for v in counts.values())
    # Check that sum of counts equals NUM_SHOTS
    assert sum(counts.values()) == NUM_SHOTS


def test_execute_circuit_result_format(sample_qasm3):
    """Test that circuit execution returns proper format."""
    circuit = parse_qasm3(sample_qasm3)
    counts = execute_circuit(circuit)

    # Result should be a dictionary with string keys (bit strings)
    assert all(isinstance(k, str) for k in counts.keys())
    assert all(isinstance(v, int) and v >= 0 for v in counts.values())
