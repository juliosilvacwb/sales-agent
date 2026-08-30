<!-- markdownlint-disable MD013 -->
# T013: Data Queried Flag and Response Grounding

## PRD Reference

- **PRD:** [R013-data-queried-flag.md](../business-requirements/R013-data-queried-flag.md)

## Technical Goal

Enhance executive trust in the Sales Data Analysis Agent by providing transparent UI grounding. The orchestrator will track LangChain tool executions per turn and inject a deterministic `data_queried: true` flag into the `ChatResponseDTO` whenever factual database tools are invoked. The frontend will dynamically render a "Verified Data" badge to distinguish factual analytics from probabilistic conversational chit-chat.

## Architecture Decisions (ADRs)

### ADR-01: LangChain Callback Interception

- **Decision:** The backend orchestrator will utilize a custom LangChain `BaseCallbackHandler` (e.g., `ToolTrackingCallbackHandler`) injected into the `AgentExecutor` to monitor `on_tool_start` or `on_tool_end` events during a single turn.
- **Rationale:** This is the most non-invasive and deterministic method to intercept agent reasoning steps in LangChain. It avoids parsing raw LLM text or modifying the core tool implementations.

### ADR-02: Strict Per-Turn Isolation via Request Scoping

- **Decision:** The `ToolTrackingCallbackHandler` will be instantiated per `ask()` request (request-scoped) rather than residing as a stateful property on the long-lived `SalesAgent` instance.
- **Rationale:** Prevents historical conversational turns from "bleeding" into new turns (BR03, PRD04). If the callback handler state was persisted globally, a database query on Turn 1 would incorrectly flag a simple greeting on Turn 2 as "verified".

### ADR-03: DTO Enrichment over Raw JSON

- **Decision:** The `data_queried` flag will be explicitly added as a typed attribute to `ChatResponseDTO`.
- **Rationale:** Maintains type safety (R012) and clear API contracts across the Hexagonal Application boundary, instead of dynamically patching JSON dictionaries in the controller.

## Security and Reliability

### Security Mitigations

- **UI Spoofing Prevention:** The frontend must derive the verified badge exclusively from the API's `data_queried` boolean property, completely ignoring any markdown hallucinations (e.g., the LLM trying to print "✅ Dados Verificados" in its own text).

### Reliability

- **Latency:** The callback handler acts strictly in memory, intercepting string events. The latency overhead is O(1) and safely within the sub-1ms budget (NFR02).

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Application Contract (Zero Dependencies)

#### Phase 1 tasks (all parallel-safe)

- [ ] Task 001 - [Domain-Model]: Update `ChatResponseDTO` with `data_queried` (Depends On: —)

### 🟡 Phase 2 — Orchestration and Interception (Depends on Phase 1)

#### Phase 2 tasks (all parallel-safe)

- [ ] Task 002 - [UseCase]: Implement `ToolTrackingCallbackHandler` for LangChain (Depends On: Task 001)
- [ ] Task 003 - [UseCase]: Update `SalesAgent.ask` to inject callback and return flag (Depends On: Task 002)
- [ ] Task 004 - [UseCase]: Update `WebChatApplicationService` to map flag to DTO (Depends On: Task 003)

### 🟢 Phase 3 — Web Adapter and Validation (Depends on Phase 2)

#### Phase 3 tasks (all parallel-safe)

- [ ] Task 005 - [Adapter-Web]: Update Frontend UI to render Verified Badge (Depends On: Task 004)
- [ ] Task 006 - [Test-Integration]: Implement E2E tests for turn isolation and badge logic (Depends On: Task 005)

## Task Detailing (Summary Tasks)

### Task 001 - [Domain-Model]: Update ChatResponseDTO with data_queried

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** —
- **Objective:** Extend the API contract to support response grounding.
- **Files/Path:** `src/application/dto/chat_dto.py`
- **Reuse:** Existing `ChatResponseDTO`.
- **Technical Acceptance Criteria:**
  - Add `data_queried: bool = False` to the Pydantic model / Dataclass.
  - Ensure existing controller logic remains compatible.

---

### Task 002 - [UseCase]: Implement ToolTrackingCallbackHandler

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** —
- **Objective:** Create a request-scoped interceptor to detect database tool usage.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py` (or a dedicated utilities module)
- **Reuse:** LangChain `BaseCallbackHandler`.
- **Technical Acceptance Criteria:**
  - Create a class extending `BaseCallbackHandler`.
  - Implement `on_tool_end(self, run_manager, name: str, **kwargs)`.
  - Set a boolean flag (e.g., `self.has_queried_data = True`) if `name` matches any of the known domain tools or `secured_sql_query`.

---

### Task 003 - [UseCase]: Update SalesAgent.ask to inject callback

- **Phase:** 2
- **Depends On:** Task 002
- **Parallel With:** —
- **Objective:** Bind the callback to the execution trace and return the evaluation.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py`
- **Reuse:** Existing `ask()` method.
- **Technical Acceptance Criteria:**
  - Update `ask()` signature to return a `tuple[str, bool]` or a dedicated `AgentResult` object containing `(response_text, data_queried)`.
  - Instantiate a new `ToolTrackingCallbackHandler` inside `ask()`.
  - Pass the handler to `self._executor.invoke({"messages": messages}, config={"callbacks": [handler]})`.
  - Return `handler.has_queried_data`.

---

### Task 004 - [UseCase]: Update WebChatApplicationService to map flag

- **Phase:** 2
- **Depends On:** Task 003
- **Parallel With:** —
- **Objective:** Bridge the LLM adapter response to the Application DTO.
- **Files/Path:** `src/application/service/web_chat_application_service.py`
- **Reuse:** Existing `process_chat_message` method.
- **Technical Acceptance Criteria:**
  - Unpack the tuple/result from `SalesAgent.ask()`.
  - Pass the `data_queried` boolean directly into the instantiation of `ChatResponseDTO`.

---

### Task 005 - [Adapter-Web]: Update Frontend UI to render Verified Badge

- **Phase:** 3
- **Depends On:** Task 004
- **Parallel With:** —
- **Objective:** Translate the boolean flag into a premium aesthetic UI element.
- **Files/Path:** `src/adapter/inbound/web/static/app.js` and CSS styles.
- **Reuse:** Existing chat bubble DOM logic.
- **Technical Acceptance Criteria:**
  - Inspect the JSON response payload in `app.js` for `data_queried`.
  - If `true`, dynamically append a styled `div` (e.g., `✅ Dados Verificados`) below the assistant's text inside the message bubble container.
  - Implement premium styling (glassmorphism/emerald green accent).
  - Ensure the badge is omitted cleanly if `false` or undefined.

---

### Task 006 - [Test-Integration]: Implement E2E tests for turn isolation

- **Phase:** 3
- **Depends On:** Task 005
- **Parallel With:** —
- **Objective:** Prove factual determinism and prevent turn bleeding.
- **Files/Path:** `tests/integration/test_data_queried_flag.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Test Turn 1: Ask analytical question. Assert DTO returns `data_queried = True`.
  - Test Turn 2: Ask a general greeting using the same session history. Assert DTO returns `data_queried = False`.
  - Assert the callback handler adds zero observable latency.

## Verification Plan

### Automated Tests

- Validate LangChain callback logic via unit tests mocking `on_tool_end` events.
- Execute full API integration tests simulating chained conversational turns to assert flag isolation.

### Manual Verification

- Open the local Web UI.
- Type: "Olá!". Verify the response appears without the green badge.
- Type: "Qual o total de vendas de Março?". Verify the agent executes the tool and the response renders the `✅ Dados Verificados` badge.
