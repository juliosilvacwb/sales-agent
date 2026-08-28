from fastapi import APIRouter, Depends
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO
from src.application.port.inbound.web_chat_use_case import WebChatUseCase
from src.application.service.web_chat_application_service import WebChatApplicationService
from src.adapter.inbound.llm.sales_agent import SalesAgent

router = APIRouter()

# A simple dependency provider for the use case
def get_web_chat_use_case() -> WebChatUseCase:
    # We would normally use a proper DI container, but for this task we instantiate directly or use a singleton.
    # Note: Since the application service holds state (_active_sessions), we should ideally have a singleton of it.
    pass

# We create a simple singleton for the scope of the app
_app_service_instance = None

def get_web_chat_use_case_singleton() -> WebChatUseCase:
    global _app_service_instance
    if _app_service_instance is None:
        def agent_factory():
            # Adjust according to how SalesAgent is initialized in this project
            agent = SalesAgent()
            agent.initialize()
            return agent
        _app_service_instance = WebChatApplicationService(agent_factory=agent_factory)
    return _app_service_instance


@router.post("/chat", response_model=ChatResponseDTO)
def process_chat(
    request: ChatRequestDTO,
    use_case: WebChatUseCase = Depends(get_web_chat_use_case_singleton)
) -> ChatResponseDTO:
    """Endpoint for processing chat messages."""
    response = use_case.process_chat_message(request)
    return response
