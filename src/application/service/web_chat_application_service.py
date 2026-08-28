"""Application service for Web Chat."""
import logging
from collections import OrderedDict
from typing import Any, Callable, Dict
from src.application.port.inbound.web_chat_use_case import WebChatUseCase
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO

logger = logging.getLogger(__name__)

DEFAULT_MAX_ACTIVE_SESSIONS = 500


class WebChatApplicationService(WebChatUseCase):
    """Service that orchestrates the chat agent per session with memory bounding and error sanitization."""
    
    def __init__(self, agent_factory: Callable[[], Any], max_active_sessions: int = DEFAULT_MAX_ACTIVE_SESSIONS):
        """
        Args:
            agent_factory: A callable that returns a new instance of the SalesAgent.
            max_active_sessions: Maximum number of active session agent instances in memory (LRU eviction).
        """
        self._agent_factory = agent_factory
        self._max_active_sessions = max_active_sessions
        self._active_sessions: OrderedDict[str, Any] = OrderedDict()

    def process_chat_message(self, request: ChatRequestDTO) -> ChatResponseDTO:
        """Processes the chat message by routing it to the session's agent."""
        try:
            if request.session_id in self._active_sessions:
                # Mark session as recently used
                self._active_sessions.move_to_end(request.session_id)
            else:
                # Evict oldest session if limit reached
                if len(self._active_sessions) >= self._max_active_sessions:
                    evicted_session, _ = self._active_sessions.popitem(last=False)
                    logger.info("Evicted oldest session from active pool: %s", evicted_session)
                    
                self._active_sessions[request.session_id] = self._agent_factory()
                
            agent = self._active_sessions[request.session_id]
            
            logger.info("Processing chat message for session_id: %s", request.session_id)
            # Reusing the 'ask' method from SalesAgent
            answer = agent.ask(request.message)
            return ChatResponseDTO(response=answer, status="success")
        except Exception as e:
            logger.exception("Unexpected error processing chat message for session %s", request.session_id)
            return ChatResponseDTO(
                response="An unexpected error occurred while processing your request. Please try again later.",
                status="error"
            )
