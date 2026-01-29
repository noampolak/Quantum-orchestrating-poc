"""Temporal worker configuration and startup."""

import asyncio
import logging
import os
from temporalio.client import Client
from temporalio.worker import Worker

from app.temporal.workflows import QuantumCircuitWorkflow
from app.temporal.activities import execute_quantum_circuit_activity

logger = logging.getLogger(__name__)

# Configuration
TEMPORAL_SERVER_ADDRESS = os.getenv("TEMPORAL_SERVER_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TASK_QUEUE = "quantum-tasks"


async def main():
    """Main function to run the Temporal worker."""
    logger.info(
        "Starting Temporal worker",
        extra={
            "task_queue": TASK_QUEUE,
            "server_address": TEMPORAL_SERVER_ADDRESS,
            "namespace": TEMPORAL_NAMESPACE,
        },
    )

    # Connect to Temporal Server
    try:
        client = await Client.connect(
            TEMPORAL_SERVER_ADDRESS,
            namespace=TEMPORAL_NAMESPACE,
        )
        logger.info("Connected to Temporal Server")
    except Exception as e:
        logger.error(
            "Failed to connect to Temporal Server",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise

    # Create and run worker
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[QuantumCircuitWorkflow],
        activities=[execute_quantum_circuit_activity],
    )

    logger.info(
        "Worker started",
        extra={
            "task_queue": TASK_QUEUE,
            "workflows": ["QuantumCircuitWorkflow"],
            "activities": ["execute_quantum_circuit_activity"],
        },
    )

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
    except Exception as e:
        logger.error(
            "Worker error",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise
    finally:
        try:
            if hasattr(client, 'close'):
                await client.close()
        except Exception as e:
            logger.warning(f"Error closing Temporal client: {e}")
        logger.info("Worker stopped")


if __name__ == "__main__":
    # Setup logging before running worker
    from app.config.logging import setup_logging
    setup_logging()
    asyncio.run(main())
