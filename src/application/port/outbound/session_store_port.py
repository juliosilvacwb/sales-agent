"""Output Port for conversational session history persistence."""
from abc import ABC, abstractmethod
from langchain_core.chat_history import BaseChatMessageHistory


class SessionStorePort(ABC):
    """Abstract port defining contracts for reading, writing, and clearing session histories."""

    @abstractmethod
    def get_history(self, session_id: str) -> BaseChatMessageHistory:
        """Retrieves or initializes the chat history for the given session ID.
        
        Args:
            session_id: Unique session identifier.
            
        Returns:
            BaseChatMessageHistory instance containing past messages.
        """
        pass

    @abstractmethod
    def save_history(self, session_id: str, history: BaseChatMessageHistory) -> None:
        """Persists or refreshes the chat history for the given session ID.
        
        Args:
            session_id: Unique session identifier.
            history: The chat message history to store.
        """
        pass

    @abstractmethod
    def clear_history(self, session_id: str) -> None:
        """Deletes the conversational history associated with the session ID.
        
        Args:
            session_id: Unique session identifier.
        """
        pass

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """Checks if a session history exists in the persistence layer.
        
        Args:
            session_id: Unique session identifier.
            
        Returns:
            True if session exists, False otherwise.
        """
        pass
