"""Quantum circuit execution using Qiskit."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Number of shots for circuit execution
NUM_SHOTS = 1024


def parse_qasm3(qasm3_string: str):
    """
    Parse QASM3 string into a QuantumCircuit object.
    
    Args:
        qasm3_string: QASM3 formatted quantum circuit string
        
    Returns:
        QuantumCircuit object
        
    Raises:
        ValueError: If QASM3 string is invalid
    """
    # Lazy import to avoid PyO3 initialization issues in Temporal sandbox
    from qiskit.qasm3 import loads
    import re
    
    # Validate input
    if not qasm3_string or not qasm3_string.strip():
        raise ValueError("QASM3 string cannot be empty")
    
    try:
        # Remove include statements - qiskit-qasm3-import doesn't support them
        # Add standard gate definitions that are commonly used
        cleaned_qasm3 = re.sub(r'include\s+["\'][^"\']+["\']\s*;', '', qasm3_string, flags=re.IGNORECASE)
        cleaned_qasm3 = cleaned_qasm3.strip()
        
        # Check if string is empty after cleaning
        if not cleaned_qasm3:
            raise ValueError("QASM3 string is empty after processing")
        
        # Add standard gate definitions if they're not already present
        # These are the most common gates used in QASM3
        # Using QASM3 gate definition syntax
        standard_gates = """
// Standard gate definitions
gate h a { U(pi/2, 0, pi) a; }
gate x a { U(pi, 0, pi) a; }
gate y a { U(pi, pi/2, pi/2) a; }
gate z a { U(0, 0, pi) a; }
gate s a { U(0, 0, pi/2) a; }
gate sdg a { U(0, 0, -pi/2) a; }
gate t a { U(0, 0, pi/4) a; }
gate tdg a { U(0, 0, -pi/4) a; }
gate cx c, t { ctrl(1) @ x c, t; }
"""
        
        # Check if standard gates are already defined
        if 'gate h' not in cleaned_qasm3.lower():
            # Insert standard gates after OPENQASM declaration
            if cleaned_qasm3.startswith('OPENQASM'):
                lines = cleaned_qasm3.split('\n', 1)
                cleaned_qasm3 = lines[0] + '\n' + standard_gates + (lines[1] if len(lines) > 1 else '')
            else:
                cleaned_qasm3 = standard_gates + cleaned_qasm3
        
        logger.debug(
            "Parsing QASM3",
            extra={
                "qasm3_length": len(qasm3_string),
                "cleaned_length": len(cleaned_qasm3),
                "qasm3_preview": qasm3_string[:100] if len(qasm3_string) > 100 else qasm3_string,
            },
        )
        circuit = loads(cleaned_qasm3)
        logger.info(
            "QASM3 parsed successfully",
            extra={
                "qubits": circuit.num_qubits,
                "gates": circuit.size(),
            },
        )
        return circuit
    except Exception as e:
        logger.error(
            "Failed to parse QASM3",
            extra={
                "error": str(e),
                "qasm3_preview": qasm3_string[:200] if len(qasm3_string) > 200 else qasm3_string,
            },
            exc_info=True,
        )
        raise ValueError(f"Invalid QASM3 string: {str(e)}") from e


def execute_circuit(circuit) -> Dict[str, int]:
    """
    Execute a quantum circuit using AerSimulator.
    
    Args:
        circuit: QuantumCircuit object to execute
        
    Returns:
        Dictionary of measurement counts (e.g., {"00": 512, "11": 512})
        
    Raises:
        RuntimeError: If circuit execution fails
    """
    # Lazy import to avoid PyO3 initialization issues in Temporal sandbox
    from qiskit.providers.aer import AerSimulator
    
    try:
        logger.info(
            "Executing circuit",
            extra={
                "qubits": circuit.num_qubits,
                "gates": circuit.size(),
                "shots": NUM_SHOTS,
            },
        )

        # Create simulator
        simulator = AerSimulator()

        # Execute circuit
        job = simulator.run(circuit, shots=NUM_SHOTS)
        result = job.result()

        # Get counts
        counts = result.get_counts(circuit)

        logger.info(
            "Circuit executed successfully",
            extra={
                "result_count": len(counts),
                "result_keys": list(counts.keys()),
            },
        )

        return counts
    except Exception as e:
        logger.error(
            "Failed to execute circuit",
            extra={
                "error": str(e),
                "qubits": circuit.num_qubits,
            },
            exc_info=True,
        )
        raise RuntimeError(f"Circuit execution failed: {str(e)}") from e
