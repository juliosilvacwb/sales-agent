# PRD: Advanced AI Orchestration via LangGraph

## Summary

Origin: [PS014-langgraph-orchestration.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS014-langgraph-orchestration.md), Recommendation: Top Recommendation (Implement LangGraph State Machine).

The **Sales Data Analysis Agent** is currently orchestrated using LangChain's legacy `AgentExecutor` wrapper. While this abstraction facilitated initial prototyping of the Hexagonal Architecture and DuckDB analytical tools, it operates as an opaque, linear "black-box" loop. This creates substantial technical friction when implementing fine-grained routing controls, step-by-step execution observability, cyclic error-recovery loops (such as Agentic Self-Correction in R009), and deterministic response grounding inspection (Data Queried Flag in R013).

To elevate the application to the industry's State of the Art (SotA) in Generative AI engineering, this PRD specifies the migration of the cognitive engine to a **Graph-Based State Machine** orchestration powered by **LangGraph**.

By structuring the agent as an explicit, typed directed state graph (`StateGraph`) with discrete nodes (`call_model`, `tools`) and conditional routing edges, the system gains deterministic control over the reasoning lifecycle. This architectural upgrade natively supports cyclic self-healing loops, fine-grained state inspection, and robust multi-step reasoning, while maintaining strict encapsulation within the inbound LLM adapter layer (`src/adapter/inbound/llm/sales_agent.py`).

## Functional Requirements

- **PRD01 (LangGraph Dependency Integration):** The project must integrate `langgraph` (latest stable) as a core runtime dependency in `requirements.txt` and `pyproject.toml`.
- **PRD02 (StateGraph Architecture & Typed State):** The `SalesAgent` orchestrator must be refactored to compile a `StateGraph(MessagesState)`, managing conversational history, intermediate reasoning tokens, and tool results in a strongly typed state schema.
- **PRD03 (Discrete Graph Nodes Definition):** The state graph must define explicit, decoupled nodes:
  - `call_model`: Invokes the Chat Model with bound domain tools and the dynamic `SYSTEM_PROMPT`.
  - `tools`: A specialized `ToolNode` encapsulating the execution of the 10 Domain Tools and the `SecuredSQLQueryTool`.
- **PRD04 (Conditional Routing & Cyclic Execution Edges):** The graph must implement deterministic conditional routing:
  - From `call_model`: If the model output contains tool calls (`tool_calls`), conditionally transition to the `tools` node; if no tool calls are present, transition to `END` (`__end__`).
  - From `tools`: Unconditionally transition back to `call_model` with the returned `ToolMessage`s, enabling the model to synthesize the final answer or perform autonomous self-correction upon tool errors.
- **PRD05 (Bounded Loop & Recursion Protection):** The graph executor must enforce a configurable recursion limit (e.g., `recursion_limit=10`) to prevent runaway infinite loops during multi-step reasoning or repetitive self-correction attempts.
- **PRD06 (State Inspection for Response Grounding):** The orchestrator must inspect the compiled graph's executed messages state upon completion to detect the presence of `ToolMessage` instances, directly supplying the deterministic `data_queried: bool` flag required by R013.
- **PRD07 (Backward-Compatible Public Interface):** The public interface of `SalesAgent` (`ask(question: str, chat_history: Optional[Sequence[BaseMessage]]) -> str` and `chat_history: List[BaseMessage]`) must remain strictly backward compatible, ensuring zero breaking changes to FastAPI endpoints, use cases, or existing test suites.

## Non-Functional Requirements

- **Architectural Decoupling (Hexagonal Architecture):** The migration to LangGraph must be strictly confined to the inbound adapter layer (`src/adapter/inbound/llm/sales_agent.py`), leaving domain logic, ports, DuckDB persistence adapters, and REST controllers completely untouched.
- **Performance & Orchestration Overhead:** Graph compilation and node transitions must execute with sub-2ms framework overhead, keeping overall response latency dominated strictly by LLM API response times and DuckDB execution.
- **Observability & Traceability:** Graph-based execution enables granular logging of individual node entries, tool invocations, and state transitions, greatly improving production debuggability.
- **Testability & Determinism:** The graph structure must allow isolated unit testing of node behavior and edge routing logic without requiring full live LLM invocations.

## Business Rules

- **BR01 (Strict Adapter Isolation):** All LangGraph primitives (`StateGraph`, `MessagesState`, `ToolNode`, `END`) must be encapsulated within the `SalesAgent` class and never leak into domain models or application services.
- **BR02 (Cyclic Self-Healing Support):** The cyclic transition from `tools` back to `call_model` must preserve `ToolMessage` error flags (`is_error=True`) to empower the LLM to autonomously correct invalid parameters (as specified in R009).
- **BR03 (Deterministic State Termination):** Every conversational execution path must reach the `END` state within the allocated recursion limit, returning a valid natural language message to the caller.
- **BR04 (Stateless Thread Isolation):** Graph invocations must be stateless and thread-safe, supporting concurrent requests across multiple session threads without state contamination.

## Critical Data (Conceptual)

- **Graph State Schema (`MessagesState`):** Typed sequence of messages:
  - `SystemMessage`: Injected system instructions and dynamic data profile.
  - `HumanMessage`: User query text.
  - `AIMessage`: Assistant thoughts, tool call specifications, or final response text.
  - `ToolMessage`: Structured payload returned by executed domain/SQL tools.
- **Routing Decision Flags:** Conditional branch target (`"tools"` or `"__end__"`).
- **Turn Telemetry Metadata:** Execution path nodes traversed, tool execution count, recursion depth, and duration.

## User Flow

### Happy Path 1 (Analytical Query with Cyclic Tool Execution)

1. The user asks: "Qual é o faturamento total em 2024?".
2. `SalesAgent.ask` prepares the `MessagesState` and invokes the compiled LangGraph.
3. **Node `call_model`:** The LLM receives the messages and generates an `AIMessage` containing `tool_calls=[{"name": "get_total_sales_in_period", "args": {...}}]`.
4. **Conditional Edge:** Evaluates `tool_calls` exist -> routes to `tools` node.
5. **Node `tools`:** `ToolNode` executes `get_total_sales_in_period` against DuckDB and appends a `ToolMessage` with the sales JSON payload.
6. **Cyclic Edge:** Routes back to `call_model` with the updated state containing the `ToolMessage`.
7. **Node `call_model`:** The LLM reads the tool output, generates the final natural language executive summary `AIMessage` (with no tool calls).
8. **Conditional Edge:** Evaluates no tool calls -> routes to `END`.
9. The orchestrator inspects the state, flags `data_queried = True`, and returns the final answer string to the caller.

### Happy Path 2 (Direct Conversational Chit-Chat)

1. The user asks: "Olá! Quem é você?".
2. `SalesAgent.ask` passes the question into the graph.
3. **Node `call_model`:** The LLM generates an `AIMessage` with greeting text and zero tool calls.
4. **Conditional Edge:** Routes directly to `END`.
5. The orchestrator flags `data_queried = False` and returns the greeting immediately, saving unnecessary tool processing.

### Exception Path 1 (Cyclic Agentic Self-Correction)

1. The user submits a complex query where the agent generates a SQL query with a syntax error.
2. **Node `call_model`:** Generates `secured_sql_query` tool call.
3. **Node `tools`:** Catches `ToolException` and emits `ToolMessage(content="Erro de sintaxe...", is_error=True)`.
4. **Cyclic Edge:** Returns to `call_model`.
5. **Node `call_model` (Attempt 2):** LLM reads the error, diagnoses the syntax mistake, and issues a corrected `secured_sql_query` tool call.
6. **Node `tools`:** Corrected query executes successfully on DuckDB.
7. **Cyclic Edge:** Returns to `call_model`.
8. **Node `call_model` (Attempt 3):** Generates clean, accurate final response.
9. **Conditional Edge:** Routes to `END`.

### Exception Path 2 (Recursion Limit Exceeded)

1. A query triggers a repetitive failing loop that cannot be resolved.
2. The graph execution reaches the configured `recursion_limit` (e.g., 10 steps).
3. The graph catches `GraphRecursionError` gracefully and returns a standardized, polite fallback apology without crashing the process.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | `langgraph` is integrated into project dependencies and `SalesAgent` compiles a `StateGraph(MessagesState)`. | Dependency audit and instantiation unit test of the compiled graph. |
| AC02 | Analytical queries route from `call_model` to `tools` node and cyclically back to `call_model` before reaching `END`. | Graph execution trace test verifying sequential node traversal (`call_model` -> `tools` -> `call_model` -> `END`). |
| AC03 | Conversational queries without tool calls route directly from `call_model` to `END` in a single inference step. | Unit test asserting direct transition to `END` on greeting queries. |
| AC04 | Agentic self-correction loops (R009) execute cyclically through the graph, fixing errors before termination. | Integration test verifying multi-turn error recovery in the graph. |
| AC05 | Graph state inspection accurately determines whether `ToolMessage`s were emitted, powering `data_queried: bool` (R013). | Assertion test checking `data_queried` flag extraction from completed graph state. |
| AC06 | Public interface `SalesAgent.ask` and `SalesAgent.chat_history` remain 100% backward compatible. | Regression test suite execution across existing use cases and endpoints. |
| AC07 | Infinite loop protection (`recursion_limit`) halts runaway execution gracefully. | Unit test with simulated cyclic failure asserting graceful termination. |
