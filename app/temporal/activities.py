"""Temporal activity implementations for quantum circuit execution."""

import logging
import time
from typing import Dict
from uuid import UUID
from temporalio import activity

from app.core.database import get_db_context
from app.core.models import Task, TaskStatus
# Import quantum functions lazily to avoid PyO3 issues in workflow sandbox
# They will be imported when the activity actually runs

logger = logging.getLogger(__name__)


@activity.defn
async def execute_quantum_circuit_activity(task_id: str, qasm3_string: str) -> Dict[str, int]:
    """
    Activity to execute a quantum circuit.
    
    This activity:
    1. Loads the task from the database
    2. Parses the QASM3 string
    3. Executes the circuit
    4. Updates the database with results
    
    Args:
        task_id: Task UUID
        qasm3_string: QASM3 formatted quantum circuit string
        
    Returns:
        Dictionary of measurement counts
        
    Raises:
        ValueError: If task not found or QASM3 is invalid
        RuntimeError: If circuit execution fails
    """
    start_time = time.time()

    logger.info(
        "Activity started",
        extra={
            "task_id": task_id,
            "activity_type": "execute_quantum_circuit_activity",
        },
    )

    try:
        # Load task from database
        with get_db_context() as db:
            # Convert task_id string to UUID for type safety
            task_uuid = UUID(task_id)
            task = db.query(Task).filter(Task.id == task_uuid).first()
            if not task:
                raise ValueError(f"Task {task_id} not found")

            logger.info(
                "Task loaded from database",
                extra={
                    "task_id": task_id,
                    "status": task.status.value,
                },
            )

            # Import quantum functions here (lazy import to avoid PyO3 issues)
            from app.quantum.execution import parse_qasm3, execute_circuit
            
            # Parse QASM3
            logger.info(
                "Parsing QASM3",
                extra={
                    "task_id": task_id,
                    "qasm3_length": len(qasm3_string),
                },
            )
            circuit = parse_qasm3(qasm3_string)

            # Execute circuit
            logger.info(
                "Executing circuit",
                extra={
                    "task_id": task_id,
                    "circuit_qubits": circuit.num_qubits,
                    "shots": 1024,
                },
            )
            counts = execute_circuit(circuit)

            # Update database
            task.status = TaskStatus.COMPLETED
            task.result = counts
            db.commit()

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(
                "Circuit execution completed",
                extra={
                    "task_id": task_id,
                    "execution_time_ms": execution_time,
                    "result_keys": list(counts.keys()),
                    "status": "completed",
                },
            )

            return counts

    except Exception as e:
        # Mark task as failed in database
        try:
            with get_db_context() as db:
                # Convert task_id string to UUID for type safety
                task_uuid = UUID(task_id)
                task = db.query(Task).filter(Task.id == task_uuid).first()
                if task:
                    task.status = TaskStatus.FAILED
                    db.commit()
                    logger.warning(
                        "Task marked as failed",
                        extra={
                            "task_id": task_id,
                            "error": str(e),
                        },
                    )
        except Exception as db_error:
            logger.error(
                "Failed to update task status in database",
                extra={
                    "task_id": task_id,
                    "error": str(db_error),
                },
                exc_info=True,
            )

        logger.error(
            "Activity failed",
            extra={
                "task_id": task_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise
