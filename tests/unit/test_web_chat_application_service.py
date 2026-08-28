"""Unit tests for WebChatApplicationService."""
from unittest.mock import MagicMock
from src.application.dto.chat_dto import ChatRequestDTO
from src.application.service.web_chat_application_service import WebChatApplicationService


def test_process_chat_message_new_session():
    """Verify processing a message for a new session creates an agent and asks."""
    mock_agent = MagicMock()
    mock_agent.ask.return_value = "Agent response"
    
    mock_factory = MagicMock(return_value=mock_agent)
    
    service = WebChatApplicationService(agent_factory=mock_factory)
    request = ChatRequestDTO(message="Hello", session_id="session-1")
    
    response = service.process_chat_message(request)
    
    mock_factory.assert_called_once()
    mock_agent.ask.assert_called_once_with("Hello")
    assert response.response == "Agent response"
    assert response.status == "success"


def test_process_chat_message_existing_session():
    """Verify processing a message for an existing session reuses the agent."""
    mock_agent = MagicMock()
    mock_agent.ask.return_value = "Agent response 2"
    
    mock_factory = MagicMock(return_value=mock_agent)
    
    service = WebChatApplicationService(agent_factory=mock_factory)
    
    # First request
    service.process_chat_message(ChatRequestDTO(message="Hello 1", session_id="session-1"))
    
    # Second request with same session
    response = service.process_chat_message(ChatRequestDTO(message="Hello 2", session_id="session-1"))
    
    # Factory should only be called once
    mock_factory.assert_called_once()
    assert mock_agent.ask.call_count == 2
    mock_agent.ask.assert_called_with("Hello 2")
    assert response.response == "Agent response 2"


def test_process_chat_message_error_handling():
    """Verify error handling when the agent throws an exception."""
    mock_agent = MagicMock()
    mock_agent.ask.side_effect = Exception("Agent error")
    
    mock_factory = MagicMock(return_value=mock_agent)
    
    service = WebChatApplicationService(agent_factory=mock_factory)
    request = ChatRequestDTO(message="Break", session_id="session-2")
    
    response = service.process_chat_message(request)
    
    assert response.status == "error"
    assert response.response == "Agent error"
