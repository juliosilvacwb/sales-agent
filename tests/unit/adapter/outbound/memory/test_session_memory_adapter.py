import pytest
from src.adapter.outbound.memory.session_memory_adapter import SessionMemoryAdapter
from langchain_core.chat_history import BaseChatMessageHistory

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
