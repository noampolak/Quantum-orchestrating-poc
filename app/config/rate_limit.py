"""Rate limiting configuration for FastAPI."""

import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, status
from fastapi.responses import JSONResponse

# Check if rate limiting is enabled
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"] if RATE_LIMIT_ENABLED else [],
)

# Get rate limits from environment variables
RATE_LIMIT_POST_TASKS = os.getenv("RATE_LIMIT_POST_TASKS", "10/minute")
RATE_LIMIT_GET_TASK = os.getenv("RATE_LIMIT_GET_TASK", "60/minute")
RATE_LIMIT_LIST_TASKS = os.getenv("RATE_LIMIT_LIST_TASKS", "30/minute")
RATE_LIMIT_DELETE_TASK = os.getenv("RATE_LIMIT_DELETE_TASK", "20/minute")


def setup_rate_limiting(app):
    """
    Configure rate limiting for FastAPI app.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        FastAPI app with rate limiting configured
    """
    if RATE_LIMIT_ENABLED:
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    return app


def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    
    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception
        
    Returns:
        JSONResponse with 429 status
    """
    # Get retry_after if available (slowapi may not always provide it)
    retry_after = getattr(exc, 'retry_after', None)
    
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": int(retry_after) if retry_after else None,
        },
    )
    
    # Inject rate limit headers if available
    try:
        if hasattr(request.app.state, 'limiter') and hasattr(request.state, 'view_rate_limit'):
            response = request.app.state.limiter._inject_headers(
                response, request.state.view_rate_limit
            )
    except (AttributeError, KeyError):
        # Rate limiting not configured or view_rate_limit not set
        pass
    return response


def get_rate_limit_decorator(limit: str):
    """
    Get a rate limit decorator for a specific limit.
    If rate limiting is disabled, returns a no-op decorator.
    
    Args:
        limit: Rate limit string (e.g., "10/minute")
        
    Returns:
        Decorator function
    """
    if RATE_LIMIT_ENABLED:
        return limiter.limit(limit)
    else:
        # Return a no-op decorator if rate limiting is disabled
        def noop_decorator(func):
            return func

        return noop_decorator
