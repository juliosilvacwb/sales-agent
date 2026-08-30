"""Unit tests for RedisSessionAdapter."""
import json
from unittest.mock import MagicMock
import pytest
import redis
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

from src.adapter.outbound.redis.redis_session_adapter import RedisSessionAdapter
from src.domain.exception.session_exceptions import SessionConnectionError, SessionStorageError


def test_redis_session_adapter_get_history_empty():
    """Verify empty history returned when key does not exist in Redis."""
    mock_client = MagicMock()
    mock_client.get.return_value = None

    adapter = RedisSessionAdapter(redis_client=mock_client)
    history = adapter.get_history("session_1")

    assert len(history.messages) == 0
    mock_client.get.assert_called_once_with("sales_agent:session:session_1")


def test_redis_session_adapter_save_and_get_history():
    """Verify saving messages writes JSON with TTL, and retrieving parses messages correctly."""
    mock_client = MagicMock()
    stored_data = {}

    def mock_set(key, value, ex=None):
        stored_data[key] = value

    def mock_get(key):
        return stored_data.get(key)

    mock_client.set.side_effect = mock_set
    mock_client.get.side_effect = mock_get

    adapter = RedisSessionAdapter(redis_client=mock_client, ttl_seconds=3600)
    session_id = "user_42"

    # Save
    history = InMemoryChatMessageHistory()
    history.add_user_message("What was total revenue?")
    history.add_ai_message("Total revenue was R$ 10.000,00.")
    adapter.save_history(session_id, history)

    mock_client.set.assert_called_once()
    args, kwargs = mock_client.set.call_args
    assert args[0] == "sales_agent:session:user_42"
    assert kwargs["ex"] == 3600

    # Retrieve
    retrieved = adapter.get_history(session_id)
    assert len(retrieved.messages) == 2
    assert isinstance(retrieved.messages[0], HumanMessage)
    assert retrieved.messages[0].content == "What was total revenue?"
    assert isinstance(retrieved.messages[1], AIMessage)
    assert retrieved.messages[1].content == "Total revenue was R$ 10.000,00."


def test_redis_session_adapter_clear_and_exists():
    """Verify clearing key and checking exists in Redis."""
    mock_client = MagicMock()
    mock_client.exists.return_value = 1

    adapter = RedisSessionAdapter(redis_client=mock_client)
    session_id = "sess_exists"

    assert adapter.exists(session_id) is True
    mock_client.exists.assert_called_once_with("sales_agent:session:sess_exists")

    adapter.clear_history(session_id)
    mock_client.delete.assert_called_once_with("sales_agent:session:sess_exists")


def test_redis_session_adapter_connection_error_handling():
    """Verify Redis connection errors are converted into SessionConnectionError."""
    mock_client = MagicMock()
    mock_client.get.side_effect = redis.ConnectionError("Connection refused")

    adapter = RedisSessionAdapter(redis_client=mock_client)

    with pytest.raises(SessionConnectionError):
        adapter.get_history("sess_err")


def test_redis_session_adapter_corrupt_json_storage_error():
    """Verify corrupt JSON data raises SessionStorageError."""
    mock_client = MagicMock()
    mock_client.get.return_value = "invalid-non-json-data"

    adapter = RedisSessionAdapter(redis_client=mock_client)

    with pytest.raises(SessionStorageError):
        adapter.get_history("sess_corrupt")
