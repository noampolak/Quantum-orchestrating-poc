"""Unit tests for database models and utilities."""

import pytest
from datetime import datetime

from app.core.models import Task, TaskStatus
from app.core.database import Base, check_db_health


def test_task_model_creation(db_session):
    """Test creating a Task model."""
    task = Task(status=TaskStatus.PENDING)
    db_session.add(task)
    db_session.commit()

    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.result is None
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)


def test_task_status_transitions(db_session):
    """Test task status transitions."""
    task = Task(status=TaskStatus.PENDING)
    db_session.add(task)
    db_session.commit()

    # Transition to completed
    task.status = TaskStatus.COMPLETED
    task.result = {"00": 512, "11": 512}
    db_session.commit()

    assert task.status == TaskStatus.COMPLETED
    assert task.result == {"00": 512, "11": 512}

    # Transition to failed
    task.status = TaskStatus.FAILED
    db_session.commit()

    assert task.status == TaskStatus.FAILED


def test_task_model_repr(db_session):
    """Test Task model string representation."""
    task = Task(status=TaskStatus.PENDING)
    db_session.add(task)
    db_session.commit()

    repr_str = repr(task)
    assert "Task" in repr_str
    assert str(task.id) in repr_str
    assert "PENDING" in repr_str
