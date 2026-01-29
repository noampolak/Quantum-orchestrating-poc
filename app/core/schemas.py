"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.models import TaskStatus


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    qc: str = Field(..., description="QASM3 quantum circuit string", min_length=1)

    @field_validator("qc")
    @classmethod
    def validate_qasm3_size(cls, v: str) -> str:
        """Validate QASM3 string size."""
        max_size = 1048576  # 1MB default
        if len(v.encode("utf-8")) > max_size:
            raise ValueError(f"QASM3 string exceeds maximum size of {max_size} bytes")
        return v


class TaskResponse(BaseModel):
    """Schema for task response."""

    task_id: UUID
    message: str

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    """Schema for task status response."""

    status: TaskStatus
    result: Optional[Dict[str, int]] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListItem(BaseModel):
    """Schema for a single task in a list."""

    id: UUID
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for task list response with pagination."""

    tasks: List[TaskListItem]
    total: int
    limit: int
    offset: int


class TaskDeleteResponse(BaseModel):
    """Schema for task deletion response."""

    message: str
    task_id: UUID


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str
    message: str
    detail: Optional[str] = None
