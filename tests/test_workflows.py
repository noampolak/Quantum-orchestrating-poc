"""Temporal workflow tests using Temporal test framework."""

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.temporal.workflows import QuantumCircuitWorkflow
from app.temporal.activities import execute_quantum_circuit_activity


@pytest.mark.asyncio
async def test_workflow_execution():
    """Test workflow execution with mocked activity."""
    env = await WorkflowEnvironment.start_time_skipping()
    async with env:
        # Create a mock activity with the same name as the real one
        @activity.defn(name="execute_quantum_circuit_activity")
        async def mock_activity(task_id: str, qasm3_string: str):
            return {"00": 512, "11": 512}

        # Register workflow and activity
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[QuantumCircuitWorkflow],
            activities=[mock_activity],
        ):
            # Start workflow
            handle = await env.client.start_workflow(
                QuantumCircuitWorkflow.run,
                {"task_id": "test-task-id", "qasm3_string": "OPENQASM 3.0; qubit[1] q;"},
                id="test-workflow-id",
                task_queue="test-queue",
            )

            # Wait for result
            result = await handle.result()

            assert result == {"00": 512, "11": 512}


@pytest.mark.asyncio
async def test_workflow_activity_invocation():
    """Test that workflow calls activity with correct parameters."""
    env = await WorkflowEnvironment.start_time_skipping()
    async with env:
        call_params = []

        # Create a mock activity with the same name as the real one
        @activity.defn(name="execute_quantum_circuit_activity")
        async def mock_activity(task_id: str, qasm3_string: str):
            call_params.append((task_id, qasm3_string))
            return {"00": 512, "11": 512}

        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[QuantumCircuitWorkflow],
            activities=[mock_activity],
        ):
            handle = await env.client.start_workflow(
                QuantumCircuitWorkflow.run,
                {"task_id": "test-task-123", "qasm3_string": "test-qasm3"},
                id="test-workflow-id",
                task_queue="test-queue",
            )

            await handle.result()

            assert len(call_params) == 1
            assert call_params[0][0] == "test-task-123"
            assert call_params[0][1] == "test-qasm3"
