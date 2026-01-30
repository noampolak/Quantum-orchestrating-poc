"""Temporal activity tests."""

import pytest
from unittest.mock import patch
from contextlib import contextmanager
from app.temporal.activities import execute_quantum_circuit_activity
from app.core.models import Task, TaskStatus


@pytest.mark.asyncio
async def test_activity_execution_success(db_session, sample_qasm3):
    """Test successful activity execution."""
    # Create task in database
    task = Task(status=TaskStatus.PENDING)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Patch get_db_context to use test database session
    @contextmanager
    def mock_db_context():
        yield db_session
    
    with patch('app.temporal.activities.get_db_context', side_effect=mock_db_context):
        # Execute activity
        result = await execute_quantum_circuit_activity(str(task.id), sample_qasm3)

    # Check result
    assert isinstance(result, dict)
    assert len(result) > 0
    assert all(isinstance(v, int) for v in result.values())

    # Check database was updated
    db_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == result


@pytest.mark.asyncio
async def test_activity_task_not_found():
    """Test activity with non-existent task."""
    import uuid
    task_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="not found"):
        await execute_quantum_circuit_activity(task_id, "OPENQASM 3.0; qubit[1] q;")


@pytest.mark.asyncio
async def test_activity_invalid_qasm3(db_session):
    """Test activity with invalid QASM3."""
    # Create task
    task = Task(status=TaskStatus.PENDING)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Patch get_db_context to use test database session
    @contextmanager
    def mock_db_context():
        yield db_session
    
    with patch('app.temporal.activities.get_db_context', side_effect=mock_db_context):
        # Execute activity with invalid QASM3
        with pytest.raises(ValueError):
            await execute_quantum_circuit_activity(str(task.id), "INVALID QASM3")

    # Check task was marked as failed
    db_session.refresh(task)
    assert task.status == TaskStatus.FAILED
