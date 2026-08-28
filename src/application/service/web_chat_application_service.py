"""Application service for Web Chat."""
from typing import Any, Callable, Dict
from src.application.port.inbound.web_chat_use_case import WebChatUseCase
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO


class WebChatApplicationService(WebChatUseCase):
    """Service that orchestrates the chat agent per session."""
    
    def __init__(self, agent_factory: Callable[[], Any]):
        """
        Args:
            agent_factory: A callable that returns a new instance of the SalesAgent.
        """
        self._agent_factory = agent_factory
        self._active_sessions: Dict[str, Any] = {}

    def process_chat_message(self, request: ChatRequestDTO) -> ChatResponseDTO:
        """Processes the chat message by routing it to the session's agent."""
        if request.session_id not in self._active_sessions:
            self._active_sessions[request.session_id] = self._agent_factory()
            
        agent = self._active_sessions[request.session_id]
        
        try:
            # Reusing the 'ask' method from SalesAgent
            answer = agent.ask(request.message)
            return ChatResponseDTO(response=answer, status="success")
        except Exception as e:
            return ChatResponseDTO(response=str(e), status="error")
