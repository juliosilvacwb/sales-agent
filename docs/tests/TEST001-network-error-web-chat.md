# TEST001-network-error-web-chat — Test Coverage Specification

> **Source Task:** [B001-network-error-web-chat.md](../incidents/B001-network-error-web-chat.md)

## Coverage Overview

This test specification addresses the coverage gaps identified during the resolution of the B001 network error incident. It ensures that the dependencies are properly injected into the `SalesAgent` and that any exceptions during the agent initialization process are gracefully caught by the application service layer, preventing unhandled server crashes (HTTP 500).

## Test Checklist

### Task 001 - Implement the reproduction script in tests/integration/test_web_chat_incident_b001.py

- [COMPLETED] [TEST001-01] [Integration] **Test Web Chat Network Error Reproduction**
  - **Target:** `tests/integration/test_web_chat_incident_b001.py` → `test_web_chat_network_error_reproduction()`
  - **Scenario:** The chat request to a new session executes without throwing HTTP 500.
  - **Arrange:** Initialize FastAPI `TestClient` with the application instance.
  - **Act:** Post a chat request `{"message": "hello", "session_id": "test-session-123"}` to `/chat`.
  - **Assert:** The response status code is `200 OK` and the returned `status` field is either `success` or `error`.
  - **Priority:** P0 (Critical)

### Task 002 - Fix agent_factory in src/adapter/inbound/web/chat_controller.py

- [COMPLETED] [TEST001-02] [Unit] **Test Agent Factory Initializes SalesAgent with Proper DI**
  - **Target:** `src/adapter/inbound/web/chat_controller.py` → `get_web_chat_use_case_singleton()`
  - **Scenario:** The `agent_factory` passed to the singleton `WebChatApplicationService` properly instantiates a valid `SalesAgent` instance.
  - **Arrange:** Call `get_web_chat_use_case_singleton()` to retrieve the service instance.
  - **Act:** Invoke the protected `_agent_factory()` from the retrieved service instance.
  - **Assert:** The returned object is an instance of `SalesAgent` and has valid `_llm` and `_tools` initialized.
  - **Priority:** P1 (High)

### Task 003 - Move agent instantiation into try...except block in WebChatApplicationService

- [COMPLETED] [TEST001-03] [Unit] **Test WebChatApplicationService Gracefully Handles Agent Factory Errors**
  - **Target:** `src/application/service/web_chat_application_service.py` → `process_chat_message()`
  - **Scenario:** When the `agent_factory` raises an exception during agent initialization, the service catches it and returns a structured error response instead of throwing.
  - **Arrange:** Create a mock `agent_factory` that always raises an `Exception("Mock factory failure")`. Instantiate `WebChatApplicationService(agent_factory=mock_factory)`. Create a `ChatRequestDTO` payload.
  - **Act:** Call `process_chat_message(request)`.
  - **Assert:** The method returns a `ChatResponseDTO` with `status="error"` and `response="An unexpected error occurred while processing your request. Please try again later."`.
  - **Priority:** P0 (Critical)
