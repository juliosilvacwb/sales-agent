import pytest
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from src.adapter.outbound.memory.session_memory_adapter import SessionMemoryAdapter


def test_get_session_history():
    adapter = SessionMemoryAdapter()
    
    # New session should create a history
    history1 = adapter.get_session_history("session_1")
    assert isinstance(history1, BaseChatMessageHistory)
    
    # Same session should return the same history object
    history1_again = adapter.get_session_history("session_1")
    assert history1 is history1_again
    
    # Different session should return a different history object
    history2 = adapter.get_session_history("session_2")
    assert history1 is not history2


def test_session_memory_adapter_message_persistence_and_isolation():
    """Verify messages added to a session history persist and do not leak to other sessions."""
    adapter = SessionMemoryAdapter()
    
    history_a = adapter.get_session_history("sessA")
    history_b = adapter.get_session_history("sessB")

    # Add messages to sessA
    history_a.add_message(HumanMessage(content="Pergunta A"))
    history_a.add_message(AIMessage(content="Resposta A"))

    # Assert sessA has 2 messages with correct content
    assert len(history_a.messages) == 2
    assert history_a.messages[0].content == "Pergunta A"
    assert history_a.messages[1].content == "Resposta A"

    # Assert sessB remains isolated and empty
    assert len(history_b.messages) == 0


def test_session_memory_adapter_lru_eviction():
    """Verify SessionMemoryAdapter evicts oldest session when capacity limit is reached."""
    adapter = SessionMemoryAdapter(max_sessions=3)

    h1 = adapter.get_session_history("sess-1")
    h2 = adapter.get_session_history("sess-2")
    h3 = adapter.get_session_history("sess-3")

    assert len(adapter._store) == 3

    # Access sess-1 so that LRU order is sess-2, sess-3, sess-1
    _ = adapter.get_session_history("sess-1")

    # Add sess-4, which should trigger eviction of sess-2
    h4 = adapter.get_session_history("sess-4")

    assert len(adapter._store) == 3
    assert "sess-2" not in adapter._store
    assert "sess-1" in adapter._store
    assert "sess-3" in adapter._store
    assert "sess-4" in adapter._store


