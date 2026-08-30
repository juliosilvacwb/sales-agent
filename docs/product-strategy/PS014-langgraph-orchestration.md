# Product Strategy: Advanced AI Orchestration via LangGraph

## Strategic Context

The **Sales Data Analysis Agent** is currently orchestrated using LangChain's legacy `AgentExecutor` wrapper. While this allowed for rapid prototyping and validation of the Hexagonal Architecture and DuckDB integration, it operates as a "black box" `while` loop. This limits our ability to enforce deterministic routing, trace execution paths reliably, and implement resilient cyclic behaviors like Agentic Self-Correction.

To elevate the application to the industry's State of the Art (SotA) in Generative AI, we must upgrade the core cognitive engine. The strategic objective is to migrate from a legacy linear executor to a **Graph-Based State Machine** orchestration. This upgrade will natively unlock the capabilities mapped in previous strategies, specifically PS009 (Agentic Self-Correction) and PS013 (Data Queried Flag), by giving us absolute control over the agent's reasoning loop.

## Market & Competitor Analysis

The AI engineering ecosystem is rapidly shifting from rigid chains to dynamic, cyclic graphs.
- **Stateful Control:** Frameworks like **LangGraph** (and AutoGen) model AI applications as state machines (Graphs). This allows engineers to track the exact conversation state, pause execution for Human-in-the-Loop (HITL) approvals, and route errors precisely.
- **Enterprise Adoption:** Top-tier engineering teams have abandoned `AgentExecutor` because it is difficult to debug in production. LangGraph is now the official and recommended orchestration framework by LangChain for building reliable, production-ready agents.

## Ideation Results

**1. Idea Name: Migrate Orchestration to LangGraph State Machine**

- **Problem Statement:** The current agent executor is a black box, making self-correction and execution tracing difficult to implement elegantly.
- **Proposed Solution:** Refactor the internal implementation of `SalesAgent` to utilize `langgraph`. Define a `StateGraph` consisting of a `chatbot` node and a `ToolNode`. Map conditional edges to control the flow between the LLM reasoning and tool execution, enabling native cyclic loops for error recovery.
- **Inspiration/Evidence:** The current industry standard for GenAI engineering.

**2. Idea Name: Custom Python Orchestrator (While-Loop)**

- **Problem Statement:** Need more control over the agent loop without heavy framework abstractions.
- **Proposed Solution:** Discard LangChain orchestration entirely and build a custom `while` loop that calls the OpenAI/Anthropic API, parses the JSON tool calls manually, executes the Python functions, and appends the messages to the history.
- **Inspiration/Evidence:** Low-dependency engineering, preferred by teams building extremely bespoke LLM integrations.

**3. Idea Name: Stay with Legacy AgentExecutor**

- **Problem Statement:** Migration requires engineering effort and re-testing.
- **Proposed Solution:** Keep the current `create_agent` implementation and attempt to force self-correction through heavy system prompt engineering and custom output parsers.
- **Inspiration/Evidence:** "If it ain't strictly broken, don't fix it."

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Migrate to LangGraph State Machine** | 5 | 5 | 5 | 3 | 4 | **22** |
| Custom Python Orchestrator | 4 | 4 | 3 | 1 | 2 | **14** |
| Stay with Legacy AgentExecutor | 1 | 2 | 1 | 5 | 1 | **10** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement LangGraph State Machine**

We must deprecate the use of `AgentExecutor` and fully adopt **LangGraph** within our AI inbound adapter. This architectural upgrade validates our commitment to modern AI engineering practices.

- **Tradeoff Analysis:** Migrating to LangGraph requires learning a new graph-based paradigm and rewriting the agent initialization code. However, because our application follows strict Hexagonal Architecture, this change is entirely isolated to `src/adapter/inbound/llm/sales_agent.py`. The rest of the system (Domain, Tests, DuckDB Adapters) remains untouched. The massive gain in observability, error handling (PS009), and transparency (PS013) justifies the engineering effort.
- **Recommended Sequencing & Scope:**
  1. Add `langgraph` to `requirements.txt`.
  2. In `sales_agent.py`, replace `create_agent` with a `StateGraph(MessagesState)`.
  3. Define the `call_model` node (invokes the LLM) and the `tools` node (using `ToolNode(self._tools)`).
  4. Define the routing logic: if the LLM decides to call a tool, route to the `tools` node; otherwise, route to `__END__`.
  5. The cyclic nature of the graph will automatically return the execution from the `tools` node back to the `call_model` node, naturally enabling the Agentic Self-Correction loop.

## Parking Lot

- **Custom Python Orchestrator:** While building an orchestrator from scratch is a fantastic learning exercise, it introduces unnecessary maintenance burden for a production system when LangGraph natively solves the state management problem.
