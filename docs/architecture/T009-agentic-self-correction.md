<!-- markdownlint-disable MD013 -->
# T009: Agentic Self-Correction and Error Resilience

## PRD Reference

- **PRD:** [R009-agentic-self-correction.md](../business-requirements/R009-agentic-self-correction.md)

## Technical Goal

Refactor the Sales Data Analysis Agent to implement a native self-correction loop using LangChain's `ToolException`. Instead of returning error messages as successful tool outputs—which causes the LLM to expose raw SQL traces to the user—the tools will raise native exceptions. The agent executor will catch these exceptions (`handle_tool_error=True`), re-inject the error signal into the LLM context, and trigger an autonomous reasoning loop to repair the query up to a strict budget of 3 retries. This ensures zero raw error exposure (BR01) and a resilient user experience.

## Architecture Decisions (ADRs)

### ADR-01: Native ToolException over String Returns

- **Decision:** All tools (`SecuredSQLQueryTool` and functions in `domain_tools.py`) will raise `langchain_core.tools.ToolException` instead of catching exceptions and returning strings.
- **Alternatives Evaluated:**
  - *Custom JSON Error Wrappers:* Returning `{"status": "error", "message": "..."}`. Rejected because it still relies on the LLM implicitly understanding it's an error rather than utilizing the framework's native error handling lifecycle.
- **Trade-offs:** Raising exceptions forces the orchestration layer (AgentExecutor) to explicitly handle the error state, enabling built-in retry mechanics and telemetry hooks. It fully couples the error contract to LangChain's `ToolException`, which is acceptable as this is within the LLM adapter boundary.

### ADR-02: Self-Correction Boundary (Adapter Layer Isolation)

- **Decision:** All self-correction logic, `ToolException` raising, and retry configurations will be strictly confined to the `src/adapter/inbound/llm/` package. The core `SalesAnalysisUseCase` (Application) and `AdvancedMetricsService` (Domain) will remain entirely unaware of LLM-specific error handling.
- **Rationale:** Preserves Hexagonal Architecture integrity. The core application throws standard Python exceptions (e.g., `ValueError`, `duckdb.Error`); the LLM adapter catches these and translates them into LLM-digestible `ToolException`s.

### ADR-03: Max Iterations and Retry Ceiling

- **Decision:** The agent executor in `sales_agent.py` will be configured with a maximum retry budget (e.g., `max_iterations=5` total per turn, allowing ~3 tool retries) to prevent runaway token consumption and infinite loops (PRD04, BR03).
- **Trade-offs:** A strict ceiling guarantees bounded latency but introduces the risk of exhausting attempts on complex queries. This is mitigated by the graceful fallback message (PRD05) which provides a clean user experience upon exhaustion.

## Security and Reliability

### Security Mitigations

- **Error Sanitization (BR04):** Before a `ToolException` is raised, the original Python/DuckDB error string must be sanitized to redact local file paths (`[REDACTED_PATH]`) and environment variables, ensuring no host context leaks into the LLM prompt.

### Reliability

- **Deterministic Fallback:** If the self-correction loop fails 3 times, the system guarantees a standardized, polite business apology rather than crashing or exposing a stack trace.

## Technical Checklist (Atomic Tasks)

> **Note:** Because this implementation is entirely localized to the Inbound LLM Adapter, it does not modify the Domain or Application layers. The phases below represent the sequential construction of the self-correction mechanism within the adapter boundary.

### 🔵 Phase 1 — Agent Foundation (Prompts and Settings)

- [ ] Task 001 - [Config]: Update `SYSTEM_PROMPT` with self-correction instructions (Depends On: —)

### 🟡 Phase 2 — Tool Hardening (Exceptions and Handlers)

#### Phase 2 tasks (all parallel-safe)

- [ ] Task 002 - [Adapter-Web]: Refactor `SecuredSQLQueryTool` to raise sanitized `ToolException` (Depends On: Task 001)
- [ ] Task 003 - [Adapter-Web]: Refactor `domain_tools.py` to raise `ToolException` on validation errors (Depends On: Task 001)
- [ ] Task 004 - [Adapter-Web]: Implement `_handle_error` callback for Telemetry (Depends On: Task 001)

### 🟢 Phase 3 — Orchestration and Validation (Depends on Phase 2)

#### Phase 3 tasks (all parallel-safe)

- [ ] Task 005 - [UseCase]: Configure `SalesAgent` executor with error handlers and retry ceilings (Depends On: Task 002, Task 003, Task 004)
- [ ] Task 006 - [Test-Integration]: Implement self-correction E2E tests (Depends On: Task 005)

## Task Detailing (Summary Tasks)

### Task 001 - [Config]: Update SYSTEM_PROMPT with self-correction instructions

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** —
- **Objective:** Instruct the LLM on how to behave when a tool fails and returns an error signal.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py`
- **Reuse:** Existing `SYSTEM_PROMPT`.
- **Technical Acceptance Criteria:**
  - Append a new section to `SYSTEM_PROMPT` detailing Error Recovery guidelines.
  - Instruct the LLM to autonomously analyze error messages, fix the issue (e.g., hallucinated columns, syntax errors), and retry the tool.
  - Instruct the LLM to never display the raw error to the user, and use a polite fallback message if it cannot resolve the issue.

---

### Task 002 - [Adapter-Web]: Refactor SecuredSQLQueryTool to raise sanitized ToolException

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** Task 003, Task 004
- **Objective:** Replace string error returns with native `ToolException` for SQL execution failures.
- **Files/Path:** `src/adapter/inbound/llm/sql_fallback_tool.py`
- **Reuse:** Existing `SecuredSQLQueryTool` logic and sanitization regex.
- **Technical Acceptance Criteria:**
  - Import `ToolException` from `langchain_core.tools`.
  - Set `handle_tool_error = True` in the tool class definition.
  - Inside the `try...except Exception` block, replace `return f"Erro ao executar..."` with `raise ToolException(f"Erro ao executar... {sanitized_err}")`.
  - Also raise `ToolException` for security violations (forbidden keywords, missing SELECT).

---

### Task 003 - [Adapter-Web]: Refactor domain_tools.py to raise ToolException

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** Task 002, Task 004
- **Objective:** Ensure domain tools leverage the same self-correction loop for input validation failures.
- **Files/Path:** `src/adapter/inbound/llm/domain_tools.py`
- **Reuse:** Existing `create_domain_tools` factory.
- **Technical Acceptance Criteria:**
  - Import `ToolException` from `langchain_core.tools`.
  - Pass `handle_tool_error=True` to the `@tool` decorators: e.g., `@tool(handle_tool_error=True)`.
  - In `get_total_sales_in_period`, catch `ValueError` from date parsing and raise `ToolException(str(e))` instead of returning a string.

---

### Task 004 - [Adapter-Web]: Implement custom error handler for Telemetry

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** Task 002, Task 003
- **Objective:** Create a custom function to handle `ToolException`s, emit telemetry, and format the error for the LLM.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py` (or a dedicated utilities module)
- **Reuse:** Standard logging.
- **Technical Acceptance Criteria:**
  - Create a function `_handle_tool_error(error: ToolException) -> str`.
  - Emits a structured log warning: `[AGENT_SELF_CORRECTION] Tool execution failed. Providing feedback to agent. Error: {error}`.
  - Returns the error string to the LLM.

---

### Task 005 - [UseCase]: Configure SalesAgent executor with retry ceilings

- **Phase:** 3
- **Depends On:** Task 002, Task 003, Task 004
- **Parallel With:** —
- **Objective:** Wire the custom error handler to the agent executor and enforce the retry loop limits.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py`
- **Reuse:** Existing `create_agent` (AgentExecutor) instantiation.
- **Technical Acceptance Criteria:**
  - If using `AgentExecutor` (LangChain), set `max_iterations=5` (which allows ~3 retries after initial thought/action).
  - Configure the tools with the custom error handler: for each tool, set `handle_tool_error=_handle_tool_error` (the telemetry function created in Task 004).
  - Ensure the executor gracefully returns the polite fallback message if `max_iterations` is reached without crashing the application.

---

### Task 006 - [Test-Integration]: Implement self-correction E2E tests

- **Phase:** 3
- **Depends On:** Task 005
- **Parallel With:** —
- **Objective:** Validate the self-correction loop using a deterministic failing scenario.
- **Files/Path:** `tests/integration/test_agent_self_correction.py`
- **Reuse:** Existing mock dependencies.
- **Technical Acceptance Criteria:**
  - Test 1: Simulate a user asking for a hallucinated column via SQL fallback. Verify the agent receives the `ToolException`, corrects the query, and returns a successful answer in a single turn.
  - Test 2: Simulate an irrecoverable error (e.g., querying a non-existent table 3 times). Verify the agent exhausts retries and returns the polite fallback message (AC06).
  - Test 3: Verify that `[AGENT_SELF_CORRECTION]` telemetry logs are emitted during the retry process (AC07).

## Verification Plan

### Automated Tests

- Unit tests for tools asserting `pytest.raises(ToolException)`.
- Integration tests invoking the agent with mocked tools that intentionally fail to assert retry loops.

### Manual Verification

- Ask the agent an ambiguous question that forces a bad SQL query. Observe the console logs to see the `[AGENT_SELF_CORRECTION]` marker triggered, followed by the agent successfully delivering the corrected answer without user intervention.
