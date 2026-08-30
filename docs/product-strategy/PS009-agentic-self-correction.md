# Product Strategy: Agentic Self-Correction & Error Resilience

## Strategic Context

In the current implementation of the **Sales Data Analysis Agent**, whenever a backend tool fails (e.g., the `secured_sql_query` tool encounters a DuckDB syntax error or a missing column), the exception is caught and returned to the LLM as a standard text string.

Because the error is formatted as a successful string return rather than an explicit error signal, the LLM often assumes its job is complete. Consequently, it forwards the raw, technical error message directly to the end-user. This exposes backend complexity, degrades the User Experience (UX), and breaks the illusion of interacting with an intelligent assistant.

To achieve an enterprise-grade AI architecture, the system must implement **Agentic Self-Correction**. The agent must be capable of receiving a formal error signal from a tool, analyzing its own mistake (e.g., "I hallucinated a column name"), and autonomously executing a corrected tool call before ever responding to the user.

## Market & Competitor Analysis

In modern Agentic AI design (such as ReAct loops or LangGraph architectures), error handling is treated as a core conversational loop, not an application crash.

- **Self-Healing AI:** State-of-the-art products (like Devin or Advanced Data Analysis in ChatGPT) do not surface standard tool errors to the user. Instead, they use internal feedback loops to retry and fix queries.
- **Framework Native Support:** LangChain provides built-in mechanisms like `ToolException` and `ToolMessage(is_error=True)` specifically designed to tell the LLM that the previous action failed, forcing it to reason about the failure.
- Implementing this pattern dramatically increases the reliability and perceived intelligence of the application.

## Ideation Results

**1. Idea Name: Native LangChain ToolExceptions & Self-Correction Loop**

- **Problem Statement:** Tools return errors as plain strings, leading the LLM to expose raw errors to the user.
- **Proposed Solution:** Refactor all tools to raise `ToolException` instead of returning strings on failure. Configure the Agent Executor to capture these exceptions (`handle_tool_error=True`) and inject them back into the LLM's context window as explicit error messages. Update the System Prompt to instruct the LLM to read the error, reason about it, and retry up to 3 times before apologizing to the user.
- **Inspiration/Evidence:** Best practices from LangChain and LangGraph documentation for building resilient agents.

**2. Idea Name: Custom Python Retry Decorator (Blind Retries)**

- **Problem Statement:** Tools fail intermittently.
- **Proposed Solution:** Wrap the Python functions in a `@retry` decorator (e.g., using the `tenacity` library) that simply attempts to run the exact same function again if it fails.
- **Inspiration/Evidence:** Traditional software engineering resilience patterns.

**3. Idea Name: Silent Failure (Masking Errors)**

- **Problem Statement:** Users hate seeing technical errors.
- **Proposed Solution:** Catch all tool errors, log them, and always return a hardcoded string to the user like: "I am unable to access this data right now."
- **Inspiration/Evidence:** Basic UX fallback patterns.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Native ToolExceptions & Self-Correction Loop** | 5 | 5 | 5 | 3 | 4 | **22** |
| Custom Python Retry Decorator | 2 | 2 | 2 | 2 | 2 | **10** |
| Silent Failure (Masking Errors) | 3 | 4 | 2 | 4 | 3 | **16** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement Native ToolExceptions & Self-Correction Loop**

We must transition from "Error Reporting" to "Error Reasoning". By leveraging the native Agentic Self-Correction patterns, we allow the LLM to act as its own debugger, significantly boosting the success rate of complex analytical queries.

- **Tradeoff Analysis:** We reject the "Blind Retry" approach because if the LLM generates an invalid SQL query, retrying the exact same invalid query will never work; the LLM must *know* it failed so it can change the input. The tradeoff is slightly higher token consumption (as the LLM must process the error and generate a new response), which is a negligible cost compared to the massive leap in UX and reliability.
- **Recommended Sequencing & Scope:**
  1. **Refactor Tools:** In `domain_tools.py` and `sql_fallback_tool.py`, replace `except Exception as e: return f"Erro..."` with `raise ToolException(str(e))`.
  2. **Configure Executor:** Update `sales_agent.py` to ensure the agent executor is instantiated with `handle_tool_errors=True` (or equivalent configuration in LangGraph).
  3. **Update System Prompt:** Add a behavioral rule to `SYSTEM_PROMPT`: *"If a tool returns an error, DO NOT immediately inform the user. Analyze the error message, identify what went wrong in your previous tool invocation, and try again with corrected parameters. Only inform the user if you fail after multiple attempts."*

## Parking Lot

- **Silent Failure:** Discarded as a primary strategy, though a polite fallback message should be used *only* if the LLM exhausts its self-correction retries.
- **Custom Python Retry Decorator:** Useless for deterministic LLM hallucinations (like wrong SQL syntax), but could be useful for handling transient network errors if we integrate external APIs in the future.
