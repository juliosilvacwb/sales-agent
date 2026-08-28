from typing import Dict
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory

class SessionMemoryAdapter:
    """In-memory persistence for chat sessions."""
    
    def __init__(self):
        self._store: Dict[str, BaseChatMessageHistory] = {}
        
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Retrieves or creates a chat message history for the given session ID."""
        if session_id not in self._store:
            self._store[session_id] = InMemoryChatMessageHistory()
        return self._store[session_id]

# Singleton instance for the application
session_memory_adapter = SessionMemoryAdapter()
