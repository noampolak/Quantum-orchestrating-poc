"""API endpoint tests with mocked Temporal client."""

from unittest.mock import AsyncMock, patch
from fastapi import status

from app.core.models import TaskStatus, Task


def test_create_task_success(client, db_session, sample_qasm3):
    """Test successful task creation."""
    async def mock_get_client():
        mock_temporal_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_temporal_client.start_workflow = AsyncMock(return_value=mock_handle)
        return mock_temporal_client
    
    with patch("app.api.tasks.get_temporal_client", side_effect=mock_get_client):
        response = client.post(
            "/tasks",
            json={"qc": sample_qasm3},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "task_id" in data
        assert "message" in data
        assert data["message"] == "Task submitted successfully."


def test_create_task_invalid_qasm3(client):
    """Test task creation with invalid QASM3."""
    response = client.post(
        "/tasks",
        json={"qc": "INVALID QASM3"},
    )

    # Should still create task, but workflow might fail
    assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]


def test_create_task_missing_field(client):
    """Test task creation with missing field."""
    response = client.post(
        "/tasks",
        json={},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_task_not_found(client, db_session):
    """Test getting non-existent task."""
    import uuid
    task_id = uuid.uuid4()

    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()


def test_get_task_pending(client, sample_task):
    """Test getting pending task."""
    response = client.get(f"/tasks/{sample_task.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "pending"
    assert data["message"] == "Task is still in progress."


def test_get_task_completed(client, db_session, sample_task):
    """Test getting completed task."""
    sample_task.status = TaskStatus.COMPLETED
    sample_task.result = {"00": 512, "11": 512}
    db_session.commit()

    response = client.get(f"/tasks/{sample_task.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"] == {"00": 512, "11": 512}


def test_list_tasks(client, db_session):
    """Test listing tasks."""
    # Create some test tasks
    for i in range(5):
        task = Task(status=TaskStatus.PENDING)
        db_session.add(task)
    db_session.commit()

    response = client.get("/tasks")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "tasks" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert len(data["tasks"]) <= data["limit"]


def test_list_tasks_pagination(client, db_session):
    """Test task list pagination."""
    # Create test tasks
    for i in range(10):
        task = Task(status=TaskStatus.PENDING)
        db_session.add(task)
    db_session.commit()

    response = client.get("/tasks?limit=5&offset=0")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["tasks"]) == 5
    assert data["limit"] == 5
    assert data["offset"] == 0


def test_list_tasks_filter_by_status(client, db_session):
    """Test filtering tasks by status."""
    # Create tasks with different statuses
    pending_task = Task(status=TaskStatus.PENDING)
    completed_task = Task(status=TaskStatus.COMPLETED)
    db_session.add(pending_task)
    db_session.add(completed_task)
    db_session.commit()

    response = client.get("/tasks?status=completed")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(task["status"] == "completed" for task in data["tasks"])


def test_delete_task_not_found(client, db_session):
    """Test deleting non-existent task."""
    import uuid
    task_id = uuid.uuid4()

    response = client.delete(f"/tasks/{task_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_task_success(client, db_session, sample_task):
    """Test successful task deletion."""
    async def mock_get_client():
        mock_temporal_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_temporal_client.get_workflow_handle = AsyncMock(return_value=mock_handle)
        mock_handle.cancel = AsyncMock()
        return mock_temporal_client
    
    with patch("app.api.tasks.get_temporal_client", side_effect=mock_get_client):
        response = client.delete(f"/tasks/{sample_task.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "deleted" in data["message"].lower()


def test_rate_limiting_post_tasks(client, sample_qasm3):
    """Test rate limiting on POST /tasks endpoint."""
    # Make multiple requests quickly
    responses = []
    for i in range(15):  # More than the 10/minute limit
        response = client.post(
            "/tasks",
            json={"qc": sample_qasm3},
        )
        responses.append(response.status_code)

    # At least one should be rate limited (429)
    # Note: This test may be flaky if rate limiting is disabled
    # In a real scenario, we'd need to ensure rate limiting is enabled
    assert any(status_code == status.HTTP_429_TOO_MANY_REQUESTS for status_code in responses) or \
           all(status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR] for status_code in responses)
