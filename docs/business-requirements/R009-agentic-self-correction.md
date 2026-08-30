# PRD: Agentic Self-Correction and Error Resilience

## Summary

Origin: [PS009-agentic-self-correction.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS009-agentic-self-correction.md), Recommendation: Top Recommendation (Implement Native ToolExceptions & Self-Correction Loop).

In the current implementation of the **Sales Data Analysis Agent**, whenever a backend tool fails (such as the `SecuredSQLQueryTool` encountering a DuckDB syntax error, a hallucinated column name, or a domain tool receiving invalid parameters), the exception is caught and returned to the LLM as a plain text string.

Because the error is returned as an ordinary successful tool output rather than an explicit error signal, the LLM frequently assumes its task is complete and forwards the raw, technical error string directly to the end-user. This exposes internal database complexity, degrades the user experience, and breaks the persona of an intelligent AI assistant.

This PRD specifies the transition to a native **Agentic Self-Correction & Error Resilience** architecture. By refactoring tools to raise native `ToolException`s and configuring the agent executor to feed explicit error feedback into the LLM context, the agent will autonomously reason about its mistakes (e.g., repairing malformed SQL clauses, correcting column names, or adjusting parameter types) and execute corrected tool invocations before delivering a finalized, accurate response to the user.

## Functional Requirements

- **PRD01 (Explicit Tool Error Signaling via ToolException):** All Domain Tools (`domain_tools.py`) and Fallback Tools (`sql_fallback_tool.py`) must raise `ToolException` on execution failures, invalid inputs, or database errors instead of returning error text strings.
- **PRD02 (Agent Executor Error Capture & Re-Injection):** The agent executor in `sales_agent.py` must configure tool error handling (`handle_tool_error=True` or a custom exception handler) to capture `ToolException`s and re-inject structured error signals into the conversational reasoning loop without aborting the agent run.
- **PRD03 (Self-Correction Prompting & Behavioral Rules):** The `SYSTEM_PROMPT` must be updated with strict self-healing rules instructing the LLM that whenever a tool execution fails, it must analyze the error message, identify the root cause of the failure, and re-attempt the tool call with corrected arguments.
- **PRD04 (Bounded Self-Correction Retry Budget):** The agent must enforce a maximum retry threshold (up to 3 consecutive self-correction attempts per user query) to prevent infinite loops, excessive latency, or runaway token consumption.
- **PRD05 (Graceful Fallback on Retry Exhaustion):** If the agent exhausts its self-correction attempts without resolving the error, it must deliver a polite, user-friendly business apology (e.g., explaining that the requested information could not be retrieved with the available parameters) rather than exposing raw technical stack traces.
- **PRD06 (Telemetry & Observability for Self-Correction):** The system must log self-correction telemetry events (`[AGENT_SELF_CORRECTION]`), recording the tool name, attempt number, error signature, and whether the self-correction ultimately succeeded or was exhausted.

## Non-Functional Requirements

- **User Experience & Persona Integrity:** End-users must never be presented with raw SQL syntax errors, DuckDB internal traces, or unformatted Python exception strings.
- **Latency & Token Budget Control:** Self-correction loops must only trigger on actual tool errors. Bounding retries to 3 attempts ensures overall query latency remains within acceptable operational thresholds.
- **Information Security & Path Sanitization:** Error messages packaged into `ToolException` must redact local file paths (`[REDACTED_PATH]`) and sensitive credentials before reaching the LLM context.
- **Architectural Decoupling (Hexagonal Architecture):** Tool exceptions and self-correction handlers must be contained entirely within the inbound LLM adapter layer (`src/adapter/inbound/llm/`), keeping core domain and application use cases independent of LLM error structures.

## Business Rules

- **BR01 (Zero Raw Error Exposure):** Technical error messages, raw SQL tracebacks, and internal schema failure traces must never be displayed to the end-user.
- **BR02 (Autonomous Diagnosis First):** Upon receiving a tool error, the agent must autonomously attempt to diagnose and correct the input at least once before presenting any failure response to the user.
- **BR03 (Strict Retry Ceiling):** An agent turn must not exceed 3 self-correction iterations for a single user query. If attempt 3 fails, the agent must transition to the graceful fallback message.
- **BR04 (Sanitized Error Propagation):** All exception messages passed to `ToolException` must be sanitized to prevent host environment data leakage.

## Critical Data (Conceptual)

- **Tool Exception Payload:** Exception class, sanitized error description, and contextual correction guidance.
- **Self-Correction Turn State:** Cumulative attempt counter, previous failed tool calls, and revised tool parameters.
- **Self-Healing Telemetry Record:** Timestamp, `session_id`, tool name, error type, retry count, and final resolution status (`RESOLVED` or `EXHAUSTED`).
- **User-Facing Fallback Template:** Standardized executive response used when self-correction fails to resolve the issue.

## User Flow

### Happy Path (Autonomous SQL Column Hallucination Repair)

1. The user asks: "Qual é o faturamento total do produto Product_0001?".
2. The AI Agent attempts a fallback query: `SELECT SUM(total_price) FROM sales_data WHERE product_id = 'Product_0001'`.
3. `SecuredSQLQueryTool` attempts execution on DuckDB. DuckDB fails because column `total_price` does not exist.
4. The tool raises `ToolException("Erro SQL: Coluna 'total_price' não encontrada na tabela 'sales_data'. Colunas disponíveis: planned_quantity, actual_quantity, planned_price, actual_price, ...")`.
5. The agent executor catches the exception and returns the error feedback message to the LLM.
6. The LLM reads the error, realizes that revenue is calculated as `SUM(actual_quantity * actual_price)`, and immediately executes a corrected tool call: `SELECT SUM(actual_quantity * actual_price) AS faturamento FROM sales_data WHERE product_id = 'Product_0001'`.
7. DuckDB executes the corrected query successfully and returns the data.
8. The agent presents the final revenue figure clearly to the user, completely transparent of the intermediate correction.

### Exception Path 1 (SQL Syntax Self-Correction)

1. The user requests a complex aggregation.
2. The agent generates a query with a missing `GROUP BY` clause.
3. The tool raises `ToolException` with the DuckDB syntax error message.
4. The agent inspects the error, adds the missing `GROUP BY` clause on Attempt 2, and successfully completes the analysis.

### Exception Path 2 (Exhaustion of Self-Correction Retries)

1. The user asks a question involving data not present in the dataset.
2. The agent attempts 3 different tool calls or query reformulations, all failing with `ToolException`.
3. The agent reaches the maximum retry limit of 3 attempts.
4. The agent gracefully halts and replies to the user: "Não foi possível localizar os dados necessários para responder à sua solicitação com a estrutura atual do dataset. Por favor, verifique se a informação desejada está disponível ou reformule sua pergunta.".

### Exception Path 3 (Domain Tool Input Validation Self-Correction)

1. The agent invokes a domain tool (e.g., `get_total_sales_in_period`) with an invalid date format (e.g., `2024/01/01` instead of `01/01/2024`).
2. The domain tool raises `ToolException("Formato de data inválido. Utilize o padrão DD/MM/YYYY.")`.
3. The agent catches the exception, reformats the date strings to `DD/MM/YYYY`, and re-invokes the domain tool successfully.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | `SecuredSQLQueryTool` and domain tools raise `ToolException` on SQL syntax errors, missing columns, and invalid arguments. | Unit tests asserting `pytest.raises(ToolException)` on tool failure cases. |
| AC02 | Agent executor is configured with `handle_tool_error=True` to catch `ToolException` without crashing the application. | Integration test invoking agent with an intentionally failing tool. |
| AC03 | `SYSTEM_PROMPT` contains explicit self-correction instructions guiding the LLM to diagnose and retry upon tool errors. | Prompt inspection asserting the presence of self-healing behavioral rules. |
| AC04 | Agent autonomously fixes a hallucinated SQL column name within the same conversational turn without user intervention. | End-to-end integration test verifying multi-step self-correction execution. |
| AC05 | Retry budget ceiling (maximum 3 correction iterations) is enforced, preventing runaway loops. | Unit/Integration test with a persistently failing tool asserting termination after 3 retries. |
| AC06 | When retries are exhausted, the agent delivers a polite business apology without exposing raw stack traces. | Output text assertion verifying exclusion of SQL/Python error traces. |
| AC07 | Telemetry logs emit `[AGENT_SELF_CORRECTION]` markers detailing the tool name, retry attempt, and resolution status. | Log capture validation during self-correction test runs. |
