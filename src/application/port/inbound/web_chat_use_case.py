"""Inbound port for Web Chat Use Case."""
from abc import ABC, abstractmethod
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO


class WebChatUseCase(ABC):
    """Interface for the web chat use case.
    
    This port defines how the web adapter (FastAPI) interacts with the application core.
    """
    
    @abstractmethod
    def process_chat_message(self, request: ChatRequestDTO) -> ChatResponseDTO:
        """Processes an incoming chat message and returns a response.
        
        Args:
            request: The chat request containing message and session_id.
            
        Returns:
            The chat response containing the agent's text and status.
        """
        pass
