# Quantum Circuit Execution System

A production-ready asynchronous quantum circuit execution system built with FastAPI, Temporal, PostgreSQL, and Qiskit. This system accepts QASM3 quantum circuits, executes them asynchronously using Temporal workflows, and provides a REST API for task submission and status retrieval.

## Architecture Overview

The system follows an asynchronous task processing architecture using Temporal for durable workflow orchestration:

```
Client → FastAPI → PostgreSQL (task storage)
              ↓
         Temporal Server (workflow orchestration)
              ↓
    ┌──────────┴──────────┐
    ↓                     ↓
Worker-1              Worker-2 (and more...)
    ↓                     ↓
Activities → Qiskit → Results → PostgreSQL
```

### Key Features

- **Asynchronous Execution**: Tasks are processed asynchronously using Temporal workflows
- **Durable Execution**: Tasks never lost, even if workers crash
- **High Availability**: Multiple workers provide redundancy and parallel processing
- **Rate Limiting**: Per-endpoint rate limiting to protect the API
- **Structured Logging**: JSON logging with correlation IDs for full request tracing
- **Health Checks**: Database and Temporal Server connectivity monitoring
- **RESTful API**: Complete REST API with OpenAPI/Swagger documentation

## Technology Stack

- **FastAPI**: Modern Python web framework
- **Temporal**: Durable workflow orchestration
- **PostgreSQL**: Persistent task storage
- **Qiskit**: Quantum circuit execution
- **Poetry**: Dependency management
- **Docker Compose**: Container orchestration

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Python 3.11+ and Poetry for local development

### Running with Docker Compose

1. Clone the repository:
```bash
git clone <repository-url>
cd Quantum-orchestrating-poc
```

2. Start all services:
```bash
docker-compose up --build
```

This will start:
- **API Server** on `http://localhost:8000`
- **Temporal UI** on `http://localhost:8088`
- **PostgreSQL** on `localhost:5432`
- **Temporal Server** on `localhost:7233`
- **2 Worker instances** for task processing

3. Access the API:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Temporal UI: http://localhost:8088

## API Endpoints

### POST /tasks

Submit a quantum circuit for execution.

**Request:**
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "qc": "OPENQASM 3.0; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c[0] = measure q[0]; c[1] = measure q[1];"
  }'
```

**Note:** The `include "stdgates.inc";` statement is optional and will be automatically handled by the parser.

**Response:**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Task submitted successfully."
}
```

**Rate Limit:** 10 requests per minute per IP

### GET /tasks/{task_id}

Get the status and result of a task.

**Request:**
```bash
curl http://localhost:8000/tasks/123e4567-e89b-12d3-a456-426614174000
```

**Response (Pending):**
```json
{
  "status": "pending",
  "message": "Task is still in progress."
}
```

**Response (Completed):**
```json
{
  "status": "completed",
  "result": {"00": 512, "11": 512}
}
```

**Response (Failed):**
```json
{
  "status": "failed",
  "message": "Task execution failed."
}
```

**Response (Not Found - 404):**
```json
{
  "status": "error",
  "message": "Task not found."
}
```

**Rate Limit:** 60 requests per minute per IP

### GET /tasks

List all tasks with pagination and filtering.

**Request:**
```bash
curl "http://localhost:8000/tasks?status=completed&limit=10&offset=0"
```

**Response:**
```json
{
  "tasks": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "completed",
      "created_at": "2024-01-15T10:30:45Z",
      "updated_at": "2024-01-15T10:30:50Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

**Query Parameters:**
- `status` (optional): Filter by status (pending, completed, failed)
- `limit` (optional): Number of tasks per page (1-100, default: 50)
- `offset` (optional): Number of tasks to skip (default: 0)

**Rate Limit:** 30 requests per minute per IP

### DELETE /tasks/{task_id}

Delete a task. If the task is pending or running, the associated Temporal workflow will be cancelled before deletion.

**Request:**
```bash
curl -X DELETE http://localhost:8000/tasks/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "message": "Task deleted successfully.",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Rate Limit:** 20 requests per minute per IP

### GET /health

Health check endpoint.

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "ok",
  "temporal": "ok"
}
```

## QASM3 Format

The system accepts quantum circuits in OpenQASM 3.0 format. The system automatically handles standard gate definitions, so `include` statements are optional and will be automatically processed.

**Example:**
```qasm
OPENQASM 3.0;

qubit[2] q;
bit[2] c;

h q[0];        // Hadamard gate
cx q[0], q[1]; // CNOT gate

c[0] = measure q[0];
c[1] = measure q[1];
```

**Note:** If you include `include "stdgates.inc";` in your QASM3, it will be automatically stripped and standard gates (h, x, y, z, s, sdg, t, tdg, cx) will be injected automatically by the parser.

## Configuration

Configuration is done via environment variables in `docker-compose.yml`. For local development, you can create a `.env` file or set environment variables directly.

**Available environment variables:**
- `DATABASE_URL`: PostgreSQL connection string
- `TEMPORAL_SERVER_ADDRESS`: Temporal Server address (default: `temporal-server:7233`)
- `TEMPORAL_NAMESPACE`: Temporal namespace (default: `default`)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `RATE_LIMIT_ENABLED`: Enable/disable rate limiting (default: `true`)
- `RATE_LIMIT_*`: Per-endpoint rate limits (e.g., `RATE_LIMIT_POST_TASKS=10/minute`)

## Testing

### Running Tests

**Using Docker (Recommended):**
```bash
# Build and run all tests
docker-compose --profile test build test
docker-compose --profile test run --rm test
```

**Using Poetry (Local Development):**
```bash
# Fast Tests (unit, API, workflow, activity):
poetry run pytest tests/test_unit.py tests/test_api.py tests/test_workflows.py tests/test_activities.py tests/test_quantum.py

# Integration Tests:
poetry run pytest tests/test_integration.py -m integration

# All Tests:
poetry run pytest
```

### Test Structure

- `tests/test_unit.py`: Unit tests for models and utilities
- `tests/test_quantum.py`: Quantum execution logic tests
- `tests/test_api.py`: API endpoint tests (with mocked Temporal)
- `tests/test_workflows.py`: Temporal workflow tests
- `tests/test_activities.py`: Temporal activity tests
- `tests/test_integration.py`: End-to-end integration tests

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry (install from https://python-poetry.org/docs/#installation)
- Docker and Docker Compose (for PostgreSQL and Temporal Server)

### Local Development

1. Install Poetry (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies:
```bash
poetry install
```

3. Activate Poetry shell:
```bash
poetry shell
```

4. (Optional) Set up environment variables:
```bash
# Create .env file if you want to override docker-compose.yml settings
# Otherwise, environment variables are already configured in docker-compose.yml
```

5. Start PostgreSQL and Temporal Server:
```bash
docker-compose up db temporal-server temporal-ui -d
```

6. Initialize database:
```bash
poetry run python -c "from app.core.database import init_db; init_db()"
```

7. Run API server:
```bash
poetry run uvicorn app.main:app --reload
```

8. Run worker (in separate terminal):
```bash
poetry run python -m app.temporal.worker
```

## Project Structure

```
app/
├── api/                    # API routes
│   ├── __init__.py
│   └── tasks.py           # Task endpoints (POST, GET, DELETE)
├── core/                   # Core application components
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy database models
│   ├── schemas.py         # Pydantic request/response schemas
│   └── database.py        # Database connection and session management
├── config/                 # Configuration modules
│   ├── __init__.py
│   ├── logging.py        # Structured JSON logging setup
│   └── rate_limit.py      # Rate limiting configuration
├── quantum/                # Quantum circuit execution
│   ├── __init__.py
│   └── execution.py       # QASM3 parsing and circuit execution
├── temporal/               # Temporal workflow orchestration
│   ├── __init__.py
│   ├── client.py         # Temporal client connection
│   ├── workflows.py      # Workflow definitions
│   ├── activities.py     # Activity implementations
│   └── worker.py         # Worker startup script
└── main.py                # FastAPI application entrypoint

tests/                      # Test suite
├── test_unit.py          # Unit tests
├── test_api.py           # API endpoint tests
├── test_quantum.py       # Quantum execution tests
├── test_workflows.py    # Temporal workflow tests
├── test_activities.py   # Temporal activity tests
└── test_integration.py   # End-to-end integration tests
```

## Architecture Decisions

### Why Temporal?

- **Durable Execution**: Tasks survive worker crashes and restarts
- **Automatic Retries**: Built-in retry policies for failed activities
- **Workflow History**: Complete audit trail of all executions
- **Scalability**: Easy horizontal scaling of workers

### Why Multiple Workers?

- **Redundancy**: If one worker fails, others continue processing
- **Parallel Processing**: Multiple tasks execute concurrently
- **High Availability**: No single point of failure

### Rate Limiting Strategy

Different endpoints have different rate limits based on resource usage:
- **POST /tasks**: 10/min (most resource-intensive)
- **GET /tasks/{id}**: 60/min (read-only, allows frequent polling)
- **GET /tasks**: 30/min (database query)
- **DELETE /tasks/{id}**: 20/min (write operation)

## Monitoring

### Logs

All logs are in structured JSON format for easy parsing:
```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "INFO",
  "logger": "app.activities",
  "message": "Circuit execution completed",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
  "execution_time_ms": 1250
}
```

### Temporal UI

Access Temporal UI at http://localhost:8088 to:
- View workflow executions
- Monitor task queues
- Inspect workflow history
- Debug failed workflows

## Troubleshooting

### Database Connection Issues

Check that PostgreSQL is running:
```bash
docker-compose ps db
```

Verify connection string in `docker-compose.yml` or your `.env` file.

### Temporal Server Connection Issues

Check that Temporal Server is running:
```bash
docker-compose ps temporal-server
```

Verify `TEMPORAL_SERVER_ADDRESS` in `docker-compose.yml` or your `.env` file.

### Worker Not Processing Tasks

1. Check worker logs:
```bash
docker-compose logs worker-1
```

2. Verify worker is connected to Temporal Server
3. Check that workflows and activities are registered

