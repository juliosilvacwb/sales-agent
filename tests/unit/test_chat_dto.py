"""Unit tests for Chat DTOs."""
import pytest
from pydantic import ValidationError
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO


def test_chat_request_dto_valid():
    """Verify ChatRequestDTO can be instantiated with valid data."""
    req = ChatRequestDTO(message="Hello", session_id="123")
    assert req.message == "Hello"
    assert req.session_id == "123"


def test_chat_response_dto_valid():
    """Verify ChatResponseDTO can be instantiated with valid data."""
    res = ChatResponseDTO(response="Hi there")
    assert res.response == "Hi there"
    assert res.status == "success"


def test_chat_request_dto_boundary_and_pattern_validation():
    """Verify ChatRequestDTO enforces min_length, max_length, and regex pattern constraints."""
    # Valid message and session_id
    valid_dto = ChatRequestDTO(message="A" * 4000, session_id="valid_session-123")
    assert len(valid_dto.message) == 4000
    assert valid_dto.session_id == "valid_session-123"

    # Empty message
    with pytest.raises(ValidationError):
        ChatRequestDTO(message="", session_id="sess123")

    # Message too long (> 4000 chars)
    with pytest.raises(ValidationError):
        ChatRequestDTO(message="A" * 4001, session_id="sess123")

    # Empty session_id
    with pytest.raises(ValidationError):
        ChatRequestDTO(message="Hello", session_id="")

    # Session_id too long (> 128 chars)
    with pytest.raises(ValidationError):
        ChatRequestDTO(message="Hello", session_id="s" * 129)

    # Invalid characters in session_id
    with pytest.raises(ValidationError):
        ChatRequestDTO(message="Hello", session_id="session with spaces")

    with pytest.raises(ValidationError):
        ChatRequestDTO(message="Hello", session_id="session!@#$")

