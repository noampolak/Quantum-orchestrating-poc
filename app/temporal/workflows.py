"""Temporal workflow definitions for quantum circuit execution."""

import logging
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from app.temporal.activities import execute_quantum_circuit_activity

logger = logging.getLogger(__name__)


@workflow.defn
class QuantumCircuitWorkflow:
    """Workflow for executing quantum circuits."""

    @workflow.run
    async def run(self, workflow_input: dict) -> dict:
        """
        Execute quantum circuit workflow.
        
        Args:
            workflow_input: Dictionary with 'task_id' and 'qasm3_string'
            
        Returns:
            Dictionary with execution result
        """
        task_id = workflow_input["task_id"]
        qasm3_string = workflow_input["qasm3_string"]
        
        workflow_id = workflow.info().workflow_id

        logger.info(
            "Workflow started",
            extra={
                "workflow_id": workflow_id,
                "task_id": task_id,
                "workflow_type": "QuantumCircuitWorkflow",
            },
        )

        try:
            # Execute activity with retry policy
            # Pass activity arguments as a tuple to work with SDK signature
            result = await workflow.execute_activity(
                execute_quantum_circuit_activity,
                args=(task_id, qasm3_string),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                ),
            )

            logger.info(
                "Workflow completed successfully",
                extra={
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                },
            )

            return result
        except Exception as e:
            logger.error(
                "Workflow failed",
                extra={
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
