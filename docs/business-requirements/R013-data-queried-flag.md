# PRD: Data Queried Flag and Response Grounding

## Summary

Origin: [PS013-data-queried-flag.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS013-data-queried-flag.md), Recommendation: Top Recommendation (Implement Data Queried Boolean Flag).

In enterprise sales and financial analytics, executive trust is paramount. Business leaders using the **Sales Data Analysis Agent** make high-stakes operational and commercial decisions based on reported numbers.

Currently, the agent returns responses as plain text without metadata indicating whether the answer was fetched from the underlying database or generated from probabilistic model memory. This creates an ungrounded "black box" experience, forcing users to wonder whether a reported metric was factually calculated or hallucinated by the LLM.

This PRD specifies the implementation of a **Data Queried Flag (`data_queried`)** response grounding mechanism. The backend orchestrator tracks intermediate tool activity during each conversational turn and includes a deterministic boolean flag `data_queried: true` in the API response DTO whenever an analytical domain tool or SQL fallback tool is successfully executed. The Web Chat UI visualizes this flag by rendering an elegant, verified data badge (`✅ Dados Verificados`) beneath the assistant's message bubble, providing immediate transparency and user confidence.

## Functional Requirements

- **PRD01 (Tool Execution Interception & Turn Grounding):** The agent orchestrator (`sales_agent.py` and application service) must track all tool invocations during a conversational turn to determine if any analytical domain tool or SQL fallback tool was executed.
- **PRD02 (API Response DTO Enrichment):** The API response schema (`ChatResponseDTO`) for `POST /chat` must include the boolean field `data_queried: bool` (defaulting to `false`).
- **PRD03 (Deterministic State Flag Evaluation):**
  - `data_queried = true`: when at least one analytical tool (any of the 10 Domain Tools or `secured_sql_query`) was invoked and returned data during the current turn.
  - `data_queried = false`: when the turn was purely conversational (e.g., greetings, general capabilities explanations) or when no data tools were invoked.
- **PRD04 (Per-Turn Isolation):** The `data_queried` flag must be strictly evaluated per conversational turn, preventing tool executions from previous turns from incorrectly flagging subsequent casual chat turns.
- **PRD05 (Frontend Verified Data Badge):** The web chat interface (`index.html` / `app.js` / CSS) must inspect the `data_queried` attribute on incoming assistant responses:
  - If `true`, render a verified badge with a shield/checkmark icon and label `"Dados Verificados"` (or `"Baseado em dados reais"`) anchored to the message bubble.
  - If `false`, omit the badge cleanly.
- **PRD06 (Backward Compatibility):** The API endpoint must maintain full backward compatibility for existing client consumers while providing the extended JSON payload.

## Non-Functional Requirements

- **Aesthetic Excellence & Premium UI:** The verified data badge must feature modern, premium styling (e.g., subtle green emerald tone, glassmorphism accent, and smooth entrance transition) matching the web interface's visual standard.
- **Performance & Latency Overhead:** Flag evaluation during response serialization must occur in memory in sub-1ms, adding zero observable latency to API responses.
- **Architectural Decoupling (Hexagonal Architecture):** DTO enrichment and flag tracking must reside within the inbound presentation/API adapter layer, preserving domain layer independence.
- **Factual Determinism:** Zero false positives on the grounding flag; the badge must appear if and only if real data querying occurred.

## Business Rules

- **BR01 (Strict Grounding Truth):** `data_queried` must never be set to `true` unless an analytical tool was executed and returned valid results during the specific request turn.
- **BR02 (Conversational Transparency):** Chit-chat, greetings, policy rejections, and clarification questions must always return `data_queried: false`.
- **BR03 (Isolated Turn Lifecycle):** Historical conversational messages reloaded from session storage must retain their respective per-turn grounding state without cross-turn bleeding.
- **BR04 (Graceful UI Omission):** If the `data_queried` property is absent or `false`, the frontend must smoothly omit the badge without layout shifting or rendering empty containers.

## Critical Data (Conceptual)

- **Chat Request Payload:** `session_id` (string), `message` (string).
- **Chat Response Payload (DTO):**
  - `session_id` (string): Conversational session identifier.
  - `response` (string): Assistant's natural language markdown response.
  - `data_queried` (boolean): Flag indicating whether factual analytical data tools were invoked.
- **Intermediate Execution State:** List of executed tool names and outcome statuses captured during agent reasoning.

## User Flow

### Happy Path 1 (Factual Sales Analytical Query)

1. The user asks: "Qual é o produto mais vendido em volume?".
2. The AI Agent invokes `get_top_selling_product` domain tool.
3. The domain tool returns sales data from DuckDB.
4. The agent formulates the textual response.
5. The backend orchestrator detects tool invocation and sets `data_queried: true` in `ChatResponseDTO`.
6. The frontend receives the payload and renders the assistant's message bubble with a green `✅ Dados Verificados` badge at the bottom.
7. The user gains immediate confidence that the reported figures are grounded in real database records.

### Happy Path 2 (General Chit-Chat / Greeting)

1. The user sends: "Olá! Como você pode me ajudar hoje?".
2. The AI Agent replies with an overview of its analytical capabilities without invoking any database tools.
3. The backend orchestrator evaluates that no tools were called and sets `data_queried: false`.
4. The frontend receives the response and renders the message cleanly without the verified badge.

### Exception Path 1 (Tool Error / Unresolved Query)

1. The user asks an out-of-scope query where tools fail or no data is retrieved.
2. The agent returns a polite fallback apology without successful data retrieval.
3. The backend evaluates that no valid data tool completed successfully, returning `data_queried: false`.
4. The frontend renders the apology without misleading verification badges.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | `ChatResponseDTO` includes `data_queried: bool = False` in the API contract. | Schema inspection and serialization test of `ChatResponseDTO`. |
| AC02 | Responses to analytical queries that execute Domain Tools or SQL fallback return `data_queried: true`. | Integration test verifying `data_queried: true` on domain tool invocations. |
| AC03 | Responses to conversational greetings, clarifications, and help requests return `data_queried: false`. | Integration test asserting `data_queried: false` on generic conversational inputs. |
| AC04 | Multi-turn conversations accurately isolate the flag per turn without history pollution. | Multi-turn integration test asserting distinct flags across alternating query and chit-chat turns. |
| AC05 | Web chat frontend dynamically renders `✅ Dados Verificados` badge when `data_queried === true`. | Browser / frontend unit test asserting badge rendering on verified responses. |
| AC06 | Web chat frontend cleanly omits the verification badge when `data_queried === false`. | Frontend DOM verification asserting absence of badge element on unverified responses. |
| AC07 | In-memory flag tracking adds less than 1ms latency to overall response serialization. | API response benchmarking test. |
