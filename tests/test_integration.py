"""Integration tests for full end-to-end flow."""

import pytest
from unittest.mock import patch
from app.temporal.activities import execute_quantum_circuit_activity


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_flow(client, db_session, sample_qasm3):
    """
    Test full end-to-end workflow:
    1. POST /tasks - Create task
    2. Execute activity directly (simulating worker) - Update database
    3. Poll GET /tasks/{id} - Verify completion
    4. Verify result
    """
    # Step 1: Create task
    response = client.post(
        "/tasks",
        json={"qc": sample_qasm3},
    )

    assert response.status_code == 201
    task_id = response.json()["task_id"]

    # Step 2: Execute the activity directly to simulate worker execution
    # In a real environment, a Temporal worker would pick this up
    # For integration tests, we execute it directly
    from contextlib import contextmanager
    
    @contextmanager
    def mock_db_context():
        yield db_session
    
    with patch('app.temporal.activities.get_db_context', side_effect=mock_db_context):
        # Execute the activity that would normally be run by a Temporal worker
        await execute_quantum_circuit_activity(task_id, sample_qasm3)

    # Step 3: Verify completion
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    
    # Step 4: Verify result
    assert "result" in data
    assert isinstance(data["result"], dict)
    assert len(data["result"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_lifecycle(client, db_session, sample_qasm3):
    """Test complete task lifecycle."""
    # Create task
    response = client.post("/tasks", json={"qc": sample_qasm3})
    assert response.status_code == 201
    task_id = response.json()["task_id"]

    # Check initial status
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    # Execute activity to simulate worker execution
    from contextlib import contextmanager
    
    @contextmanager
    def mock_db_context():
        yield db_session
    
    with patch('app.temporal.activities.get_db_context', side_effect=mock_db_context):
        await execute_quantum_circuit_activity(task_id, sample_qasm3)

    # Verify completion
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "result" in response.json()


@pytest.mark.integration
def test_list_tasks_integration(client, db_session, sample_qasm3):
    """Test listing tasks in integration scenario."""
    # Create multiple tasks
    task_ids = []
    for i in range(3):
        response = client.post("/tasks", json={"qc": sample_qasm3})
        if response.status_code == 201:
            task_ids.append(response.json()["task_id"])

    # List tasks
    response = client.get("/tasks")
    assert response.status_code == 200

    data = response.json()
    assert "tasks" in data
    assert len(data["tasks"]) >= len(task_ids)


@pytest.mark.integration
def test_delete_task_integration(client, sample_qasm3):
    """Test deleting a task."""
    # Create task
    response = client.post("/tasks", json={"qc": sample_qasm3})
    if response.status_code == 201:
        task_id = response.json()["task_id"]

        # Delete task
        response = client.delete(f"/tasks/{task_id}")
        assert response.status_code == 200

        # Verify task is deleted
        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == 404
