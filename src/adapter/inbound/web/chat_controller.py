"""Web Chat REST Controller."""
from fastapi import APIRouter, Depends
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO
from src.application.port.inbound.web_chat_use_case import WebChatUseCase
from src.application.service.web_chat_application_service import WebChatApplicationService
from src.adapter.inbound.cli.main import bootstrap_agent
from src.adapter.outbound.session_factory import SessionFactory

router = APIRouter()

_app_service_instance = None


def get_web_chat_use_case_singleton() -> WebChatUseCase:
    """Dependency injection provider for stateless WebChatUseCase."""
    global _app_service_instance
    if _app_service_instance is None:
        def agent_factory():
            return bootstrap_agent()
        session_store = SessionFactory.get_session_store()
        _app_service_instance = WebChatApplicationService(
            agent_factory=agent_factory,
            session_store=session_store,
        )
    return _app_service_instance


@router.post("/chat", response_model=ChatResponseDTO)
def process_chat(
    request: ChatRequestDTO,
    use_case: WebChatUseCase = Depends(get_web_chat_use_case_singleton)
) -> ChatResponseDTO:
    """Endpoint for processing chat messages."""
    response = use_case.process_chat_message(request)
    return response
