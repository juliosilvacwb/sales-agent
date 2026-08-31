"""Application service for Web Chat."""
import logging
from typing import Any, Callable, Optional
from src.application.port.inbound.web_chat_use_case import WebChatUseCase
from src.application.port.outbound.session_store_port import SessionStorePort
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO
from src.domain.model.session_context import SessionContext

logger = logging.getLogger(__name__)


class WebChatApplicationService(WebChatUseCase):
    """Stateless service that orchestrates chat requests using decoupled session storage."""
    
    def __init__(
        self,
        agent_factory: Callable[[], Any],
        session_store: Optional[SessionStorePort] = None,
    ) -> None:
        """
        Args:
            agent_factory: A callable that returns an instance of the SalesAgent.
            session_store: Output port for persisting and retrieving conversational sessions.
        """
        self._agent_factory = agent_factory
        self._session_store = session_store

    def set_session_store(self, session_store: SessionStorePort) -> None:
        """Sets the session store adapter."""
        self._session_store = session_store

    def _extract_response_and_flag(self, result: Any) -> tuple[str, bool]:
        """Extracts natural language response and data_queried boolean flag from agent result."""
        if hasattr(result, "response") and hasattr(result, "data_queried"):
            return str(result.response), bool(result.data_queried)
        if isinstance(result, tuple) and len(result) >= 2:
            return str(result[0]), bool(result[1])
        return str(result), bool(getattr(result, "data_queried", False))

    def process_chat_message(self, request: ChatRequestDTO) -> ChatResponseDTO:
        """Processes the chat message in a completely stateless manner per compute node."""
        try:
            SessionContext.validate_session_id(request.session_id)
            logger.info("Processing chat message for session_id: %s", request.session_id)

            agent = self._agent_factory()

            if self._session_store is not None:
                history = self._session_store.get_history(request.session_id)
                prior_messages = list(history.messages)
                try:
                    result = agent.ask(request.message, chat_history=prior_messages)
                except TypeError:
                    result = agent.ask(request.message)

                answer, data_queried = self._extract_response_and_flag(result)

                # Persist turn in external store
                history.add_user_message(request.message)
                history.add_ai_message(answer)
                self._session_store.save_history(request.session_id, history)
            else:
                result = agent.ask(request.message)
                answer, data_queried = self._extract_response_and_flag(result)

            return ChatResponseDTO(response=answer, data_queried=data_queried, status="success")
        except Exception:
            logger.exception("Unexpected error processing chat message for session %s", request.session_id)
            return ChatResponseDTO(
                response="An unexpected error occurred while processing your request. Please try again later.",
                data_queried=False,
                status="error"
            )
