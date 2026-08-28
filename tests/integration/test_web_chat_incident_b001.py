import pytest
from fastapi.testclient import TestClient
from src.adapter.inbound.web.main import app

client = TestClient(app)

def test_web_chat_network_error_reproduction():
    """
    Automated Reproduction Test for the Web Chat Network Error.
    When sending a chat request to a new session, the API crashes with HTTP 500
    because of a TypeError during SalesAgent initialization.
    """
    response = client.post(
        "/chat",
        json={"message": "hello", "session_id": "test-session-123"}
    )

    # We expect the test to FAIL here right now because response.status_code is 500
    # instead of the expected 200 OK.
    # The Engineer Agent will make this test pass by fixing the DI configuration
    # and ensuring the exception handling wraps the agent factory properly.
    assert response.status_code == 200, f"Expected 200 OK but got {response.status_code}"

    data = response.json()
    assert data["status"] in ("success", "error")
