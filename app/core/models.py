"""Database models for the quantum task execution system."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, JSON, String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses String(36).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


class TaskStatus(PyEnum):
    """Task status enumeration."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    """Task model for storing quantum circuit execution tasks."""

    __tablename__ = "tasks"

    id = Column(GUID(), primary_key=True, default=lambda: uuid.uuid4(), index=True)
    status = Column(
        Enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True,
    )
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.utcnow())
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow()
    )

    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status})>"
