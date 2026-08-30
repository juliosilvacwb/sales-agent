"""Unit tests for SessionMemoryAdapter."""
from langchain_core.messages import HumanMessage, AIMessage
from src.adapter.outbound.memory.session_memory_adapter import SessionMemoryAdapter


def test_memory_adapter_get_and_save_history():
    """Verify storing and retrieving messages in SessionMemoryAdapter."""
    adapter = SessionMemoryAdapter(max_sessions=10)
    session_id = "test-session-mem"

    # Initially empty
    history = adapter.get_history(session_id)
    assert len(history.messages) == 0

    # Add messages and save
    history.add_user_message("User prompt")
    history.add_ai_message("AI answer")
    adapter.save_history(session_id, history)

    # Retrieve again
    retrieved = adapter.get_history(session_id)
    assert len(retrieved.messages) == 2
    assert retrieved.messages[0].content == "User prompt"
    assert retrieved.messages[1].content == "AI answer"
    assert adapter.exists(session_id) is True


def test_memory_adapter_clear_history():
    """Verify clearing a session in SessionMemoryAdapter."""
    adapter = SessionMemoryAdapter()
    session_id = "to-be-deleted"

    history = adapter.get_history(session_id)
    history.add_user_message("Hello")
    adapter.save_history(session_id, history)
    assert adapter.exists(session_id) is True

    adapter.clear_history(session_id)
    assert adapter.exists(session_id) is False


def test_memory_adapter_lru_eviction():
    """Verify LRU capacity bounds in SessionMemoryAdapter."""
    adapter = SessionMemoryAdapter(max_sessions=2)

    adapter.get_history("s1")
    adapter.get_history("s2")
    assert adapter.exists("s1") is True
    assert adapter.exists("s2") is True

    # Access s1 so s2 becomes oldest
    adapter.get_history("s1")

    # Add s3 -> s2 should be evicted
    adapter.get_history("s3")
    assert adapter.exists("s1") is True
    assert adapter.exists("s3") is True
    assert adapter.exists("s2") is False
