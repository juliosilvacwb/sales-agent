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
    """Verify error handling sanitizes internal exception messages returned to the client."""
    mock_agent = MagicMock()
    mock_agent.ask.side_effect = Exception("Internal database crash: connection pool exhausted")
    
    mock_factory = MagicMock(return_value=mock_agent)
    
    service = WebChatApplicationService(agent_factory=mock_factory)
    request = ChatRequestDTO(message="Break", session_id="session-2")
    
    response = service.process_chat_message(request)
    
    assert response.status == "error"
    assert response.response == "An unexpected error occurred while processing your request. Please try again later."
    assert "Internal database crash" not in response.response


def test_web_chat_application_service_session_eviction_lru():
    """Verify LRU eviction when active sessions exceed max_active_sessions."""
    created_agents = []

    def fake_agent_factory():
        agent = MagicMock()
        agent.ask.return_value = "response"
        created_agents.append(agent)
        return agent

    service = WebChatApplicationService(agent_factory=fake_agent_factory, max_active_sessions=3)

    # Add 3 sessions
    service.process_chat_message(ChatRequestDTO(message="1", session_id="sess-1"))
    service.process_chat_message(ChatRequestDTO(message="2", session_id="sess-2"))
    service.process_chat_message(ChatRequestDTO(message="3", session_id="sess-3"))

    assert len(service._active_sessions) == 3
    assert set(service._active_sessions.keys()) == {"sess-1", "sess-2", "sess-3"}

    # Touch sess-1 to make it most recently used (order becomes sess-2, sess-3, sess-1)
    service.process_chat_message(ChatRequestDTO(message="1 again", session_id="sess-1"))

    # Add 4th session (should evict sess-2)
    service.process_chat_message(ChatRequestDTO(message="4", session_id="sess-4"))

    assert len(service._active_sessions) == 3
    assert "sess-2" not in service._active_sessions
    assert "sess-1" in service._active_sessions
    assert "sess-3" in service._active_sessions
    assert "sess-4" in service._active_sessions


def test_process_chat_message_multiple_independent_sessions():
    """Verify strict isolation of agent instances between multiple concurrent sessions."""
    agent_a = MagicMock()
    agent_a.ask.return_value = "Response A"
    agent_b = MagicMock()
    agent_b.ask.return_value = "Response B"

    # Factory returns different agents on subsequent calls
    mock_factory = MagicMock(side_effect=[agent_a, agent_b])
    
    service = WebChatApplicationService(agent_factory=mock_factory)

    # Act
    response_a = service.process_chat_message(ChatRequestDTO(message="Msg A", session_id="session-A"))
    response_b = service.process_chat_message(ChatRequestDTO(message="Msg B", session_id="session-B"))

    # Assert
    assert mock_factory.call_count == 2
    assert service._active_sessions["session-A"] is agent_a
    assert service._active_sessions["session-B"] is agent_b
    assert service._active_sessions["session-A"] is not service._active_sessions["session-B"]
    
    agent_a.ask.assert_called_once_with("Msg A")
    agent_b.ask.assert_called_once_with("Msg B")
    
    assert response_a.response == "Response A"
    assert response_b.response == "Response B"


def test_web_chat_application_service_gracefully_handles_agent_factory_errors():
    """TEST001-03: Verify exception during agent factory initialization is caught and returns structured error."""
    # Arrange
    mock_factory = MagicMock(side_effect=Exception("Mock factory failure"))
    
    service = WebChatApplicationService(agent_factory=mock_factory)
    request = ChatRequestDTO(message="hello", session_id="err-session")
    
    # Act
    response = service.process_chat_message(request)
    
    # Assert
    assert response.status == "error"
    assert response.response == "An unexpected error occurred while processing your request. Please try again later."
    mock_factory.assert_called_once()
