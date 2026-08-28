"""Unit tests for Chat DTOs."""
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
