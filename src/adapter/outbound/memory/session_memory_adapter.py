"""In-memory persistence for chat sessions with bounded capacity and LRU eviction."""
from collections import OrderedDict
import threading
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from src.application.port.outbound.session_store_port import SessionStorePort
from src.domain.model.session_context import SessionContext

DEFAULT_MAX_SESSIONS = 500


class SessionMemoryAdapter(SessionStorePort):
    """In-memory persistence for chat sessions with bounded LRU eviction implementing SessionStorePort."""
    
    def __init__(self, max_sessions: int = DEFAULT_MAX_SESSIONS):
        """
        Args:
            max_sessions: Maximum number of session chat histories to keep in memory.
        """
        self._max_sessions = max_sessions
        self._store: OrderedDict[str, BaseChatMessageHistory] = OrderedDict()
        self._lock = threading.Lock()
        
    def get_history(self, session_id: str) -> BaseChatMessageHistory:
        """Retrieves or creates a chat message history for the given session ID."""
        SessionContext.validate_session_id(session_id)
        with self._lock:
            if session_id in self._store:
                self._store.move_to_end(session_id)
                return self._store[session_id]
            
            if len(self._store) >= self._max_sessions:
                self._store.popitem(last=False)
                
            history = InMemoryChatMessageHistory()
            self._store[session_id] = history
            return history

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Backward-compatible alias for get_history."""
        return self.get_history(session_id)

    def save_history(self, session_id: str, history: BaseChatMessageHistory) -> None:
        """Saves or updates the session history in memory."""
        SessionContext.validate_session_id(session_id)
        with self._lock:
            if session_id in self._store:
                self._store.move_to_end(session_id)
                self._store[session_id] = history
            else:
                if len(self._store) >= self._max_sessions:
                    self._store.popitem(last=False)
                self._store[session_id] = history

    def clear_history(self, session_id: str) -> None:
        """Removes the session from memory."""
        SessionContext.validate_session_id(session_id)
        with self._lock:
            self._store.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        """Checks if the session is present in memory."""
        SessionContext.validate_session_id(session_id)
        with self._lock:
            return session_id in self._store


# Singleton instance for the application
session_memory_adapter = SessionMemoryAdapter()
