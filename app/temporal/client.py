"""Temporal client configuration and connection."""

import os
import logging
from typing import Optional
from temporalio.client import Client

logger = logging.getLogger(__name__)

# Temporal configuration
TEMPORAL_SERVER_ADDRESS = os.getenv("TEMPORAL_SERVER_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")

# Global client instance
_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    """
    Get or create Temporal client instance.
    
    Returns:
        Temporal client instance
        
    Raises:
        RuntimeError: If client connection fails
    """
    global _client

    if _client is None:
        try:
            logger.info(
                "Connecting to Temporal Server",
                extra={
                    "address": TEMPORAL_SERVER_ADDRESS,
                    "namespace": TEMPORAL_NAMESPACE,
                },
            )
            _client = await Client.connect(
                TEMPORAL_SERVER_ADDRESS,
                namespace=TEMPORAL_NAMESPACE,
            )
            logger.info("Connected to Temporal Server successfully")
        except Exception as e:
            logger.error(
                "Failed to connect to Temporal Server",
                extra={"error": str(e), "address": TEMPORAL_SERVER_ADDRESS},
                exc_info=True,
            )
            raise RuntimeError(f"Failed to connect to Temporal Server: {str(e)}") from e

    return _client


async def close_temporal_client():
    """Close Temporal client connection."""
    global _client
    if _client is not None:
        try:
            # Temporal Python SDK client may not have an explicit close method
            # It manages connection lifecycle internally
            if hasattr(_client, 'close'):
                await _client.close()
        except Exception as e:
            logger.warning(f"Error closing Temporal client: {e}")
        finally:
            _client = None
            logger.info("Temporal client reference cleared")
