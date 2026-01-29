"""API route handlers for quantum circuit execution."""

import logging
import uuid
from typing import Optional
from uuid import UUID as UUIDType

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import Task, TaskStatus
from app.core.schemas import (
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    TaskListResponse,
    TaskListItem,
    TaskDeleteResponse,
    ErrorResponse,
)
from app.temporal.client import get_temporal_client
from app.temporal.workflows import QuantumCircuitWorkflow
from app.config.rate_limit import (
    get_rate_limit_decorator,
    RATE_LIMIT_POST_TASKS,
    RATE_LIMIT_GET_TASK,
    RATE_LIMIT_LIST_TASKS,
    RATE_LIMIT_DELETE_TASK,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a quantum circuit for execution",
)
@get_rate_limit_decorator(RATE_LIMIT_POST_TASKS)
async def create_task(
    request: Request,
    task_data: TaskCreate,
    db: Session = Depends(get_db),
):
    """
    Submit a quantum circuit in QASM3 format for asynchronous execution.
    
    Returns immediately with a task_id. The circuit will be executed
    asynchronously by a Temporal worker.
    """
    request_id = str(uuid.uuid4())

    logger.info(
        "Task creation request",
        extra={
            "request_id": request_id,
            "endpoint": "POST /tasks",
            "qasm3_length": len(task_data.qc),
        },
    )

    try:
        # Create task in database
        task = Task(status=TaskStatus.PENDING)
        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(
            "Task created in database",
            extra={
                "request_id": request_id,
                "task_id": str(task.id),
                "status": task.status.value,
            },
        )

        # Start Temporal workflow
        try:
            client = await get_temporal_client()
            workflow_id = str(task.id)

            # Start workflow - pass single dict argument to avoid SDK limitation
            handle = await client.start_workflow(
                QuantumCircuitWorkflow.run,
                {"task_id": str(task.id), "qasm3_string": task_data.qc},
                id=workflow_id,
                task_queue="quantum-tasks",
            )

            logger.info(
                "Temporal workflow started",
                extra={
                    "request_id": request_id,
                    "task_id": str(task.id),
                    "workflow_id": workflow_id,
                },
            )
        except Exception as e:
            logger.error(
                "Failed to start Temporal workflow",
                extra={
                    "request_id": request_id,
                    "task_id": str(task.id),
                    "error": str(e),
                },
                exc_info=True,
            )
            # Task is already in DB, but workflow failed to start
            # This is acceptable - the task will remain in pending state
            # and can be retried manually if needed

        return TaskResponse(task_id=task.id, message="Task submitted successfully.")

    except Exception as e:
        logger.error(
            "Task creation failed",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
            exc_info=True,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}",
        )


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get task status and result",
)
@get_rate_limit_decorator(RATE_LIMIT_GET_TASK)
async def get_task(
    request: Request,
    task_id: UUIDType,
    db: Session = Depends(get_db),
):
    """
    Retrieve the status and result of a quantum circuit execution task.
    
    Returns:
    - If completed: status and result counts
    - If pending: status and message
    - If not found: error message
    """
    logger.info(
        "Get task request",
        extra={
            "task_id": str(task_id),
            "endpoint": "GET /tasks/{task_id}",
        },
    )

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        logger.warning(
            "Task not found",
            extra={"task_id": str(task_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    if task.status == TaskStatus.COMPLETED:
        return TaskStatusResponse(
            status=task.status,
            result=task.result,
        )
    elif task.status == TaskStatus.FAILED:
        return TaskStatusResponse(
            status=task.status,
            message="Task execution failed.",
        )
    else:
        return TaskStatusResponse(
            status=task.status,
            message="Task is still in progress.",
        )


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List all tasks with pagination and filtering",
)
@get_rate_limit_decorator(RATE_LIMIT_LIST_TASKS)
async def list_tasks(
    request: Request,
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List all tasks with optional filtering by status and pagination.
    
    Query Parameters:
    - status: Filter by status (pending, completed, failed)
    - limit: Number of tasks per page (1-100, default: 50)
    - offset: Number of tasks to skip (default: 0)
    """
    logger.info(
        "List tasks request",
        extra={
            "endpoint": "GET /tasks",
            "status_filter": status_filter.value if status_filter else None,
            "limit": limit,
            "offset": offset,
        },
    )

    # Build query
    query = db.query(Task)

    if status_filter:
        query = query.filter(Task.status == status_filter)

    # Get total count
    total = query.count()

    # Apply pagination
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()

    # Convert to response format
    task_items = [
        TaskListItem(
            id=task.id,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]

    return TaskListResponse(
        tasks=task_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/{task_id}",
    response_model=TaskDeleteResponse,
    summary="Delete a task and cancel workflow if running",
)
@get_rate_limit_decorator(RATE_LIMIT_DELETE_TASK)
async def delete_task(
    request: Request,
    task_id: UUIDType,
    db: Session = Depends(get_db),
):
    """
    Delete a task. If the task is pending or running, the Temporal workflow
    will be cancelled first.
    """
    logger.info(
        "Delete task request",
        extra={
            "task_id": str(task_id),
            "endpoint": "DELETE /tasks/{task_id}",
        },
    )

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        logger.warning(
            "Task not found for deletion",
            extra={"task_id": str(task_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    # Cancel workflow if task is pending or running
    if task.status == TaskStatus.PENDING:
        try:
            client = await get_temporal_client()
            workflow_id = str(task_id)
            handle = client.get_workflow_handle(workflow_id)

            try:
                await handle.cancel()
                logger.info(
                    "Workflow cancelled",
                    extra={
                        "task_id": str(task_id),
                        "workflow_id": workflow_id,
                    },
                )
            except Exception as e:
                # Workflow might not exist or already completed
                logger.warning(
                    "Failed to cancel workflow (may not exist)",
                    extra={
                        "task_id": str(task_id),
                        "error": str(e),
                    },
                )
        except Exception as e:
            logger.error(
                "Error cancelling workflow",
                extra={
                    "task_id": str(task_id),
                    "error": str(e),
                },
                exc_info=True,
            )

    # Delete task from database
    db.delete(task)
    db.commit()

    logger.info(
        "Task deleted",
        extra={
            "task_id": str(task_id),
            "status": task.status.value,
        },
    )

    return TaskDeleteResponse(
        task_id=task_id,
        message="Task deleted successfully.",
    )
