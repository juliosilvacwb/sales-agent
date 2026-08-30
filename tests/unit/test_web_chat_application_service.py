"""Unit tests for stateless WebChatApplicationService."""
from unittest.mock import MagicMock
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from src.application.dto.chat_dto import ChatRequestDTO
from src.application.service.web_chat_application_service import WebChatApplicationService


def test_process_chat_message_with_session_store():
    """Verify processing message retrieves history from session store, asks agent, and saves history."""
    mock_agent = MagicMock()
    mock_agent.ask.return_value = "Agent response"
    mock_factory = MagicMock(return_value=mock_agent)

    mock_history = InMemoryChatMessageHistory()
    mock_session_store = MagicMock()
    mock_session_store.get_history.return_value = mock_history

    service = WebChatApplicationService(
        agent_factory=mock_factory,
        session_store=mock_session_store,
    )
    request = ChatRequestDTO(message="Hello", session_id="session-1")
    
    response = service.process_chat_message(request)
    
    mock_session_store.get_history.assert_called_once_with("session-1")
    mock_agent.ask.assert_called_once_with("Hello", chat_history=[])
    mock_session_store.save_history.assert_called_once()
    
    # Verify messages were appended to history
    assert len(mock_history.messages) == 2
    assert isinstance(mock_history.messages[0], HumanMessage)
    assert mock_history.messages[0].content == "Hello"
    assert isinstance(mock_history.messages[1], AIMessage)
    assert mock_history.messages[1].content == "Agent response"

    assert response.response == "Agent response"
    assert response.status == "success"


def test_process_chat_message_multi_turn_stateless():
    """Verify multiple requests with same session reuse history from store even with new agent instances."""
    mock_history = InMemoryChatMessageHistory()
    mock_history.add_user_message("Prior context")
    mock_history.add_ai_message("Prior response")

    mock_session_store = MagicMock()
    mock_session_store.get_history.return_value = mock_history

    mock_agent = MagicMock()
    mock_agent.ask.return_value = "Follow up response"
    mock_factory = MagicMock(return_value=mock_agent)

    service = WebChatApplicationService(
        agent_factory=mock_factory,
        session_store=mock_session_store,
    )
    request = ChatRequestDTO(message="Follow up question", session_id="session-123")

    response = service.process_chat_message(request)

    mock_session_store.get_history.assert_called_once_with("session-123")
    # Verify prior context was passed into agent.ask
    assert mock_agent.ask.call_args[1]["chat_history"] == mock_history.messages[:2]
    assert response.response == "Follow up response"
    assert len(mock_history.messages) == 4


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


def test_process_chat_message_invalid_session_id():
    """Verify invalid session_id is rejected gracefully with sanitized error response."""
    mock_factory = MagicMock()
    service = WebChatApplicationService(agent_factory=mock_factory)
    
    request = ChatRequestDTO(message="hello", session_id="session; DROP TABLE sales;--")
    response = service.process_chat_message(request)
    
    assert response.status == "error"
    mock_factory.assert_not_called()
