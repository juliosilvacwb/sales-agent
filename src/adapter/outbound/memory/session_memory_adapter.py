"""In-memory persistence for chat sessions with bounded capacity and LRU eviction."""
from collections import OrderedDict
from typing import Dict
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory

DEFAULT_MAX_SESSIONS = 500


class SessionMemoryAdapter:
    """In-memory persistence for chat sessions with bounded LRU eviction."""
    
    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS):
        """
        Args:
            max_sessions: Maximum number of session chat histories to keep in memory.
        """
        self._max_sessions = max_sessions
        self._store: OrderedDict[str, BaseChatMessageHistory] = OrderedDict()
        
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Retrieves or creates a chat message history for the given session ID."""
        if session_id in self._store:
            self._store.move_to_end(session_id)
            return self._store[session_id]
        
        if len(self._store) >= self._max_sessions:
            self._store.popitem(last=False)
            
        history = InMemoryChatMessageHistory()
        self._store[session_id] = history
        return history


# Singleton instance for the application
session_memory_adapter = SessionMemoryAdapter()
