"""Quantum circuit execution module."""

# Import only constants at module level, not Qiskit-dependent functions
# This prevents PyO3 initialization issues in Temporal's workflow sandbox
from app.quantum.execution import NUM_SHOTS

# Functions are imported lazily when needed (in activities)
__all__ = ["parse_qasm3", "execute_circuit", "NUM_SHOTS"]


def __getattr__(name):
    """Lazy import for Qiskit-dependent functions."""
    if name in ("parse_qasm3", "execute_circuit"):
        from app.quantum.execution import parse_qasm3, execute_circuit
        return parse_qasm3 if name == "parse_qasm3" else execute_circuit
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
