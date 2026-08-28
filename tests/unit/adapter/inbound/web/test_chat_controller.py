import pytest
from fastapi.testclient import TestClient
from src.adapter.inbound.web.main import app
from src.application.dto.chat_dto import ChatRequestDTO, ChatResponseDTO
from src.application.port.inbound.web_chat_use_case import WebChatUseCase

class MockWebChatUseCase(WebChatUseCase):
    def process_chat_message(self, request: ChatRequestDTO) -> ChatResponseDTO:
        if request.message == "error":
            return ChatResponseDTO(response="error generated", status="error")
        return ChatResponseDTO(response=f"echo: {request.message}", status="success")

client = TestClient(app)

def test_process_chat(mocker):
    # Mock the dependency
    from src.adapter.inbound.web.chat_controller import get_web_chat_use_case_singleton
    app.dependency_overrides[get_web_chat_use_case_singleton] = lambda: MockWebChatUseCase()
    
    response = client.post(
        "/chat",
        json={"message": "hello", "session_id": "1234"}
    )
    
    assert response.status_code == 200
    assert response.json()["response"] == "echo: hello"
    assert response.json()["status"] == "success"
    
    # Cleanup
    app.dependency_overrides.clear()


def test_process_chat_endpoint_validation_error():
    """Verify endpoint returns HTTP 422 for invalid/missing request payload."""
    app.dependency_overrides.clear()
    response = client.post(
        "/chat",
        json={"invalid_field": 123}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_get_web_chat_use_case_singleton_lifecycle(mocker):
    """Verify get_web_chat_use_case_singleton creates and caches singleton instance."""
    import src.adapter.inbound.web.chat_controller as chat_controller
    from src.application.service.web_chat_application_service import WebChatApplicationService

    # Reset singleton state
    chat_controller._app_service_instance = None

    # First call initializes singleton
    inst1 = chat_controller.get_web_chat_use_case_singleton()
    assert isinstance(inst1, WebChatApplicationService)

    # Second call returns the exact same instance
    inst2 = chat_controller.get_web_chat_use_case_singleton()
    assert inst1 is inst2


def test_agent_factory_initializes_sales_agent(mocker):
    """TEST001-02: Verify agent_factory instantiates a valid SalesAgent with properly injected DI."""
    import src.adapter.inbound.web.chat_controller as chat_controller
    from src.adapter.inbound.llm.sales_agent import SalesAgent
    
    # We must mock LLMFactory.create_llm because it requires API keys
    mock_llm = mocker.patch("src.adapter.outbound.llm.llm_factory.LLMFactory.create_llm")
    mock_llm.return_value = mocker.MagicMock()
    
    # Reset singleton state
    chat_controller._app_service_instance = None
    
    service_instance = chat_controller.get_web_chat_use_case_singleton()
    
    # Assert type to satisfy static type checkers and narrow the type
    from src.application.service.web_chat_application_service import WebChatApplicationService
    assert isinstance(service_instance, WebChatApplicationService)
    
    # Act: Invoke the factory
    agent = service_instance._agent_factory()
    
    # Assert
    assert isinstance(agent, SalesAgent)
    assert agent._llm == mock_llm.return_value
    assert len(agent._tools) > 0
