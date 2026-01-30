"""Shared pytest fixtures for testing."""

import pytest
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.core.models import Task, TaskStatus


# Use a temporary file-based database for tests (more reliable than in-memory)
# This ensures all connections see the same database
_test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
_test_db_path = _test_db_file.name
_test_db_file.close()

TEST_DATABASE_URL = f"sqlite:///{_test_db_path}"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def db_session():
    """Create a test database session and ensure tables exist."""
    # Create tables before each test (idempotent operation)
    Base.metadata.create_all(bind=test_engine)
    
    # Clear rate limiter storage before each test to prevent state persistence
    # This runs before every test (autouse=True)
    if hasattr(app.state, 'limiter'):
        limiter = app.state.limiter
        if hasattr(limiter, 'storage'):
            # Try multiple methods to clear the storage
            try:
                # Method 1: clear() method
                if hasattr(limiter.storage, 'clear'):
                    limiter.storage.clear()
                # Method 2: dict-like clear
                elif isinstance(limiter.storage, dict):
                    limiter.storage.clear()
                # Method 3: _storage internal dict
                elif hasattr(limiter.storage, '_storage'):
                    limiter.storage._storage.clear()
                # Method 4: reset() method
                elif hasattr(limiter.storage, 'reset'):
                    limiter.storage.reset()
            except:
                pass
        # Also try to reset the limiter itself
        if hasattr(limiter, 'reset'):
            try:
                limiter.reset()
            except:
                pass

    # Create session
    db = TestSessionLocal()
    try:
        yield db
        db.commit()  # Commit any pending changes
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        # Clean up: drop all tables after each test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    from unittest.mock import patch, MagicMock
    from app.config import rate_limit as rate_limit_config
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    # Disable rate limiting completely by patching at multiple levels
    def noop_decorator(limit: str):
        def decorator(func):
            # Create a wrapper that sets view_rate_limit but doesn't check limits
            import inspect
            if inspect.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    # Set view_rate_limit to None to prevent AttributeError
                    if args and hasattr(args[0], 'state'):
                        request = args[0]
                        if not hasattr(request.state, 'view_rate_limit'):
                            request.state.view_rate_limit = None
                    return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    # Set view_rate_limit to None to prevent AttributeError
                    if args and hasattr(args[0], 'state'):
                        request = args[0]
                        if not hasattr(request.state, 'view_rate_limit'):
                            request.state.view_rate_limit = None
                    return func(*args, **kwargs)
                return sync_wrapper
        return decorator
    
    # Patch RATE_LIMIT_ENABLED to False
    original_enabled = rate_limit_config.RATE_LIMIT_ENABLED
    rate_limit_config.RATE_LIMIT_ENABLED = False
    
    # Disable rate limiting by completely replacing the limiter's storage
    original_storage = None
    original_hit = None
    if hasattr(app.state, 'limiter'):
        limiter = app.state.limiter
        
        # Create a mock storage that always allows requests
        class AlwaysAllowStorage:
            """Storage that always allows requests (never rate limits)."""
            def hit(self, *args, **kwargs):
                return False  # False means not rate limited
            
            def get(self, *args, **kwargs):
                return 0  # No hits recorded
            
            def clear(self, *args, **kwargs):
                pass
            
            def reset(self, *args, **kwargs):
                pass
        
        # Replace storage with a mock that always allows requests
        if hasattr(limiter, 'storage'):
            original_storage = limiter.storage
            limiter.storage = AlwaysAllowStorage()
        
        # Also patch the hit method directly if it exists
        if hasattr(limiter, 'hit'):
            original_hit = limiter.hit
            limiter.hit = lambda *args, **kwargs: False  # Always return False (not rate limited)
    
    # Patch slowapi's extension module to handle missing view_rate_limit
    # The async_wrapper accesses request.state.view_rate_limit after the function call
    # We need to monkey-patch the State class to return None for view_rate_limit if it doesn't exist
    try:
        from starlette.datastructures import State
        original_getattr = State.__getattr__
        
        def patched_getattr(self, key):
            if key == 'view_rate_limit':
                # If view_rate_limit doesn't exist, return None instead of raising AttributeError
                try:
                    return self._state[key]
                except KeyError:
                    return None
            return original_getattr(self, key)
        
        State.__getattr__ = patched_getattr
        original_state_patch = True
    except:
        original_state_patch = False
        original_getattr = None
    
    # Patch the limiter's limit method to ensure view_rate_limit is always set
    original_limit = None
    if hasattr(app.state, 'limiter'):
        limiter = app.state.limiter
        original_limit = limiter.limit
        
        def wrapped_limit(*args, **kwargs):
            decorator = original_limit(*args, **kwargs)
            # Wrap the decorator to ensure view_rate_limit is set
            def ensure_view_rate_limit(func):
                wrapped = decorator(func)
                import inspect
                if inspect.iscoroutinefunction(func):
                    async def wrapper(*inner_args, **inner_kwargs):
                        # Ensure view_rate_limit exists before calling
                        if inner_args and hasattr(inner_args[0], 'state'):
                            if not hasattr(inner_args[0].state, 'view_rate_limit'):
                                inner_args[0].state.view_rate_limit = None
                        return await wrapped(*inner_args, **inner_kwargs)
                    return wrapper
                else:
                    def wrapper(*inner_args, **inner_kwargs):
                        # Ensure view_rate_limit exists before calling
                        if inner_args and hasattr(inner_args[0], 'state'):
                            if not hasattr(inner_args[0].state, 'view_rate_limit'):
                                inner_args[0].state.view_rate_limit = None
                        return wrapped(*inner_args, **inner_kwargs)
                    return wrapper
            return ensure_view_rate_limit
        limiter.limit = wrapped_limit
    
    # Patch the limiter's internal methods to bypass rate limit checks
    original_limiter_check = None
    original_test_window = None
    if hasattr(app.state, 'limiter'):
        limiter = app.state.limiter
        # Patch _check_request_limit if it exists
        if hasattr(limiter, '_check_request_limit'):
            original_limiter_check = limiter._check_request_limit
            limiter._check_request_limit = lambda *args, **kwargs: None
        # Patch test_window if it exists (this is what actually checks the limit)
        if hasattr(limiter, 'test_window'):
            original_test_window = limiter.test_window
            limiter.test_window = lambda *args, **kwargs: (False, None)  # (not_limited, retry_after)
    
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
            # Restore original limit if it was patched
            if original_limit and hasattr(app.state, 'limiter'):
                app.state.limiter.limit = original_limit
            # Restore original storage if it was patched
            if original_storage and hasattr(app.state, 'limiter'):
                app.state.limiter.storage = original_storage
            # Restore original hit method if it was patched
            if original_hit and hasattr(app.state, 'limiter'):
                app.state.limiter.hit = original_hit
            # Restore original limiter check if it was patched
            if original_limiter_check and hasattr(app.state, 'limiter'):
                app.state.limiter._check_request_limit = original_limiter_check
            # Restore original test_window if it was patched
            if original_test_window and hasattr(app.state, 'limiter'):
                app.state.limiter.test_window = original_test_window
            # Restore State.__getattr__ if patched
            if original_state_patch and original_getattr:
                try:
                    from starlette.datastructures import State
                    State.__getattr__ = original_getattr
                except:
                    pass
            # Restore RATE_LIMIT_ENABLED
            rate_limit_config.RATE_LIMIT_ENABLED = original_enabled
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_qasm3():
    """Sample QASM3 circuit for testing."""
    return """OPENQASM 3.0;

qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];

c[0] = measure q[0];
c[1] = measure q[1];
"""


@pytest.fixture
def sample_task(db_session):
    """Create a sample task in the database."""
    task = Task(status=TaskStatus.PENDING)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task
