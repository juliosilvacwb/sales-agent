"""Unit tests for SessionContext."""
from datetime import datetime
from src.domain.model.session_context import SessionContext


def test_session_context_instantiation():
    """Verify SessionContext can be created and has default timestamp."""
    session_id = "test-session-123"
    ctx = SessionContext(session_id=session_id)
    
    assert ctx.session_id == session_id
    assert isinstance(ctx.timestamp, datetime)


def test_session_context_custom_timestamp():
    """Verify SessionContext accepts a custom timestamp."""
    session_id = "test-session-456"
    custom_ts = datetime(2023, 1, 1, 12, 0, 0)
    ctx = SessionContext(session_id=session_id, timestamp=custom_ts)
    
    assert ctx.session_id == session_id
    assert ctx.timestamp == custom_ts
