"""Unit tests for Chat DTOs."""
import pytest
from pydantic import ValidationError
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO


def test_chat_request_dto_valid():
    """Verify ChatRequestDTO can be instantiated with valid data."""
    req = ChatRequestDTO(message="Hello", session_id="123")
    assert req.message == "Hello"
    assert req.session_id == "123"


def test_chat_response_dto_default_data_queried_false():
    """[TEST013-01] Verify ChatResponseDTO can be instantiated with valid data and default data_queried=False."""
    dto = ChatResponseDTO(response="Olá! Como posso ajudar?")
    assert dto.response == "Olá! Como posso ajudar?"
    assert dto.data_queried is False
    assert dto.status == "success"


def test_chat_response_dto_with_data_queried_true():
    """[TEST013-02] Verify ChatResponseDTO correctly holds data_queried=True."""
    dto = ChatResponseDTO(response="Produto líder: Prod_01", data_queried=True)
    assert dto.response == "Produto líder: Prod_01"
    assert dto.data_queried is True
    assert dto.status == "success"


def test_chat_response_dto_json_serialization():
    """[TEST013-03] Verify serialization of ChatResponseDTO exports data_queried as strict boolean."""
    dto = ChatResponseDTO(response="OK", data_queried=True)
    data = dto.model_dump()
    assert "data_queried" in data
    assert isinstance(data["data_queried"], bool)
    assert data["data_queried"] is True



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

