"""Unit tests for domain session exceptions."""
import pytest
from src.domain.exception.session_exceptions import (
    SessionDomainError,
    InvalidSessionIdError,
    SessionStorageError,
    SessionConnectionError,
)


def test_session_domain_error_hierarchy():
    """Verify that all session exceptions inherit from SessionDomainError."""
    assert issubclass(InvalidSessionIdError, SessionDomainError)
    assert issubclass(SessionStorageError, SessionDomainError)
    assert issubclass(SessionConnectionError, SessionStorageError)


def test_invalid_session_id_error_message():
    """Verify InvalidSessionIdError formatted message."""
    err = InvalidSessionIdError("bad session id!", "Contains spaces")
    assert "bad session id!" in str(err)
    assert "Contains spaces" in str(err)
    assert err.session_id == "bad session id!"
    assert err.reason == "Contains spaces"


def test_session_connection_error_instantiation():
    """Verify SessionConnectionError creation."""
    err = SessionConnectionError("Redis host unreachable on port 6379")
    assert "Redis host unreachable on port 6379" in str(err)
    assert isinstance(err, SessionStorageError)
