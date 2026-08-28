import pytest
from fastapi.testclient import TestClient
from src.adapter.inbound.web.main import app

# We need to mock the SalesAgent so it doesn't make real LLM calls
@pytest.fixture
def mock_sales_agent(mocker):
    from src.adapter.inbound.llm.sales_agent import SalesAgent
    
    class FakeAgent:
        def __init__(self):
            self.memory_store = []
            
        def initialize(self):
            pass
            
        def ask(self, question: str) -> str:
            self.memory_store.append(question)
            return f"Answer based on: {', '.join(self.memory_store)}"
            
    # We patch the agent factory in the chat_controller singleton
    from src.adapter.inbound.web.chat_controller import get_web_chat_use_case_singleton
    use_case = get_web_chat_use_case_singleton()
    use_case._agent_factory = lambda: FakeAgent()
    # Clear active sessions to ensure a fresh FakeAgent is used
    use_case._active_sessions = {}
    return use_case

def test_web_chat_flow(mock_sales_agent):
    client = TestClient(app)
    session_id = "test-integration-session"
    
    # First turn
    response1 = client.post(
        "/chat",
        json={"message": "What is the top product?", "session_id": session_id}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["status"] == "success"
    assert "What is the top product?" in data1["response"]
    
    # Second turn
    response2 = client.post(
        "/chat",
        json={"message": "And what is its price?", "session_id": session_id}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "success"
    # Verify memory works (the mocked agent should output both questions)
    assert "What is the top product?" in data2["response"]
    assert "And what is its price?" in data2["response"]

    # Different session
    other_session_id = "other-session"
    response3 = client.post(
        "/chat",
        json={"message": "Hello", "session_id": other_session_id}
    )
    data3 = response3.json()
    assert "What is the top product?" not in data3["response"]
    assert "Hello" in data3["response"]
