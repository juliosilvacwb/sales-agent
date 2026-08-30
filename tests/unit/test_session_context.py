"""Unit tests for SessionContext."""
from dataclasses import FrozenInstanceError
from datetime import datetime
import pytest
from src.domain.model.session_context import SessionContext
from src.domain.exception.session_exceptions import InvalidSessionIdError


def test_session_context_instantiation():
    """Verify SessionContext can be created and has default timestamp."""
    session_id = "test-session-123"
    ctx = SessionContext(session_id=session_id)
    
    assert ctx.session_id == session_id
    assert isinstance(ctx.timestamp, datetime)
    assert isinstance(ctx.created_at, datetime)
    assert isinstance(ctx.updated_at, datetime)
    assert ctx.ttl_seconds == 86400
    assert ctx.redis_key == "sales_agent:session:test-session-123"


def test_session_context_custom_timestamp():
    """Verify SessionContext accepts a custom timestamp."""
    session_id = "test-session-456"
    custom_ts = datetime(2023, 1, 1, 12, 0, 0)
    ctx = SessionContext(session_id=session_id, timestamp=custom_ts)
    
    assert ctx.session_id == session_id
    assert ctx.timestamp == custom_ts


def test_session_context_immutability():
    """Verify that SessionContext is immutable (frozen dataclass)."""
    ctx = SessionContext(session_id="session-immutable")
    with pytest.raises(FrozenInstanceError):
        setattr(ctx, "session_id", "new-id")


def test_session_context_validation_empty():
    """Verify that empty session_id raises InvalidSessionIdError."""
    with pytest.raises(InvalidSessionIdError):
        SessionContext(session_id="")


def test_session_context_validation_invalid_characters():
    """Verify that invalid characters in session_id raise InvalidSessionIdError."""
    with pytest.raises(InvalidSessionIdError):
        SessionContext(session_id="session;DROP TABLE sales;--")

    with pytest.raises(InvalidSessionIdError):
        SessionContext(session_id="session with spaces")


def test_session_context_validation_too_long():
    """Verify that session_id exceeding max length raises InvalidSessionIdError."""
    too_long = "a" * 129
    with pytest.raises(InvalidSessionIdError):
        SessionContext(session_id=too_long)


def test_format_redis_key():
    """Verify Redis key formatting and namespacing."""
    key = SessionContext.format_redis_key("sess_999")
    assert key == "sales_agent:session:sess_999"
