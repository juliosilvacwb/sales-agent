<!-- markdownlint-disable MD013 -->
# T014: Advanced AI Orchestration via LangGraph

## PRD Reference

- **PRD:** [R014-langgraph-orchestration.md](../business-requirements/R014-langgraph-orchestration.md)

## Technical Goal

Migrate the Sales Data Analysis Agent's cognitive engine from LangChain's legacy, linear `AgentExecutor` to a deterministic, graph-based state machine using LangGraph. This architecture enables explicit cyclic execution loops (essential for Agentic Self-Correction) and fine-grained state inspection (for Response Grounding/Data Queried Flags), all while keeping the public `SalesAgent.ask` interface strictly backwards compatible.

## Architecture Decisions (ADRs)

### ADR-01: LangGraph State Machine Architecture

- **Decision:** Replace `create_agent` and `AgentExecutor` with a compiled `StateGraph` utilizing `MessagesState` (a predefined typed dict containing conversational history and intermediate reasoning steps).
- **Rationale:** The legacy executor is an opaque black box. A directed state graph explicitly defines the agent's reasoning flow into decoupled nodes (`call_model`, `tools`), empowering deterministic conditional routing and cyclic self-healing loops without external side-effects.

### ADR-02: Native ToolNode Integration

- **Decision:** Utilize LangGraph's pre-built `ToolNode` to wrap the existing Domain Tools and the Secured SQL Fallback tool, rather than writing a custom execution node.
- **Rationale:** `ToolNode` automatically handles `tool_calls` parsing, parallel execution, and `ToolException` propagation (required for R009), mapping responses cleanly back into `ToolMessage`s within the state.

### ADR-03: Adapter Layer Isolation

- **Decision:** The entire LangGraph state machine will be encapsulated inside `src/adapter/inbound/llm/sales_agent.py` (or adjacent utility files in the same layer).
- **Rationale:** Adheres strictly to the Hexagonal Architecture pattern. The Application Layer (Use Cases) and Domain Layer remain completely agnostic to the underlying orchestration framework.

## Security and Reliability

### Security Mitigations

- **Infinite Loop Protection:** The graph compilation must be configured with a strict `recursion_limit` (e.g., 10) to prevent runaway token exhaustion during cyclic self-correction loops.

### Reliability

- **Deterministic Fallbacks:** If `GraphRecursionError` is raised, the `SalesAgent.ask` wrapper must catch it and return a standardized fallback message instead of crashing the API.

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Graph Foundation and Nodes (Zero Dependencies)

#### Phase 1 tasks (all parallel-safe)

- [ ] Task 001 - [Config]: Ensure `langgraph` dependency exists (Depends On: —)
- [ ] Task 002 - [Adapter-Web]: Implement discrete graph nodes (`call_model`, `tools`) (Depends On: Task 001)

### 🟡 Phase 2 — Graph Assembly and Routing (Depends on Phase 1)

#### Phase 2 tasks (all parallel-safe)

- [ ] Task 003 - [Adapter-Web]: Implement conditional routing and compile `StateGraph` (Depends On: Task 002)

### 🟢 Phase 3 — Agent Integration and Validation (Depends on Phase 2)

#### Phase 3 tasks (all parallel-safe)

- [ ] Task 004 - [Adapter-Web]: Refactor `SalesAgent` orchestration and state extraction (Depends On: Task 003)
- [ ] Task 005 - [Test-Integration]: Validate cyclic execution and backwards compatibility (Depends On: Task 004)

## Task Detailing (Summary Tasks)

### Task 001 - [Config]: Ensure langgraph dependency exists

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** —
- **Objective:** Verify and configure LangGraph as a core runtime requirement.
- **Files/Path:** `requirements.txt`, `pyproject.toml`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Verify `langgraph>=0.2.0` is installed.
  - Verify `langchain-core` is up to date for `MessagesState` compatibility.

---

### Task 002 - [Adapter-Web]: Implement discrete graph nodes

- **Phase:** 1
- **Depends On:** Task 001
- **Parallel With:** —
- **Objective:** Create the standalone execution blocks for the state machine.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py`
- **Reuse:** Existing `tools` list and `_llm` instance.
- **Technical Acceptance Criteria:**
  - Import `MessagesState`, `StateGraph`, `START`, and `END` from `langgraph.graph`.
  - Import `ToolNode` from `langgraph.prebuilt`.
  - Implement a `call_model` node function (or method): takes `MessagesState`, binds tools to the LLM (if not already bound), invokes the LLM, and returns the output `AIMessage`.
  - Instantiate a `ToolNode` using the existing array of Domain and Fallback tools.

---

### Task 003 - [Adapter-Web]: Implement conditional routing and compile StateGraph

- **Phase:** 2
- **Depends On:** Task 002
- **Parallel With:** —
- **Objective:** Wire the nodes together with logic gates.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py`
- **Reuse:** Defined nodes.
- **Technical Acceptance Criteria:**
  - Define `should_continue` conditional edge function: inspects the last message in `MessagesState`. If it has `tool_calls`, return `"tools"`. Otherwise, return `END`.
  - Build the graph:
    - Add nodes: `builder.add_node("agent", call_model)` and `builder.add_node("tools", tool_node)`.
    - Set entry point: `builder.set_entry_point("agent")`.
    - Add conditional edge from `"agent"` using `should_continue`.
    - Add unconditional edge from `"tools"` back to `"agent"`.
  - Compile the graph: `self._executor = builder.compile()`.

---

### Task 004 - [Adapter-Web]: Refactor SalesAgent orchestration

- **Phase:** 3
- **Depends On:** Task 003
- **Parallel With:** —
- **Objective:** Update the public `ask` method to execute the graph, extract responses, and preserve compatibility.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py`
- **Reuse:** Existing `ask()` signature.
- **Technical Acceptance Criteria:**
  - In `ask()`, prepare the initial `MessagesState` including the `SYSTEM_PROMPT` (as a `SystemMessage`), `chat_history`, and the new `HumanMessage`.
  - Execute the graph: `result = self._executor.invoke({"messages": messages}, config={"recursion_limit": 10})`.
  - Extract the final response text from the last `AIMessage`.
  - Iterate through `result["messages"]` to check if any `ToolMessage` instances exist. If they do, set `data_queried = True` (satisfying R013).
  - Catch `GraphRecursionError` and return a standard fallback response.

---

### Task 005 - [Test-Integration]: Validate cyclic execution and compatibility

- **Phase:** 3
- **Depends On:** Task 004
- **Parallel With:** —
- **Objective:** Guarantee that the complex graph migration does not break existing application flows.
- **Files/Path:** `tests/integration/test_sales_agent.py`
- **Reuse:** Existing test suites.
- **Technical Acceptance Criteria:**
  - All existing API tests pass without modification (validating backwards compatibility).
  - Assert that a query requiring tools successfully traverses the cyclic loop (`call_model` -> `tools` -> `call_model` -> `END`).
  - Assert that an intentional infinite loop triggers the recursion limit and fails gracefully.
