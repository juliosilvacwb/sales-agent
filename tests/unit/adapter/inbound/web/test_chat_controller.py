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
