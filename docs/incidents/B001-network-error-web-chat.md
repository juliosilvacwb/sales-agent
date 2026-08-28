# Incident Summary

- **Test Coverage:** [TEST001-network-error-web-chat.md](../tests/TEST001-network-error-web-chat.md)
- **Security Audit:** [S001-network-error-web-chat.md](../security/S001-network-error-web-chat.md)

The web chat interface displays a "Network error. Please try again." message when users attempt to send a chat request.

**Technical Analysis of the Root Cause:**
The frontend `fetch` request receives an HTTP 500 Internal Server Error, which it captures generically as a network error. On the backend, this 500 error is caused by a `TypeError: SalesAgent.__init__() missing 2 required positional arguments: 'llm' and 'tools'`.

In `src/adapter/inbound/web/chat_controller.py`, the `agent_factory` instantiates `SalesAgent()` without providing the required dependencies (`llm` and `tools`). When a new chat session is initialized in `WebChatApplicationService.process_chat_message()`, this faulty factory is called. Furthermore, the factory invocation (`self._active_sessions[request.session_id] = self._agent_factory()`) is located *outside* of the `try...except` block in the service. As a result, the exception bubbles all the way up to FastAPI, leading to an unhandled HTTP 500 error instead of a graceful JSON error payload.

## Reproduction Script (MANDATORY)

```python
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
```

## Correction Checklist (Atomic Tasks)

- [COMPLETED] Task 001 - [Test] Implement the reproduction script in `tests/integration/test_web_chat_incident_b001.py` and confirm the failure (Red).
- [COMPLETED] Task 002 - [Logic] Fix `agent_factory` in `src/adapter/inbound/web/chat_controller.py` to properly inject the `llm` and `tools` instances when instantiating `SalesAgent`.
- [COMPLETED] Task 003 - [Security/Perf] Move `self._active_sessions[request.session_id] = self._agent_factory()` into the `try...except` block in `src/application/service/web_chat_application_service.py` to ensure any initialization failures return a structured error response instead of crashing the server.
