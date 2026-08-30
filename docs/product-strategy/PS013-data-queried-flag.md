# Product Strategy: Data Queried Flag (Response Grounding)

## Strategic Context

In enterprise AI applications, **Trust and Safety** are critical barriers to user adoption. Business executives utilizing the **Sales Data Analysis Agent** must make high-stakes financial decisions based on the numbers provided by the LLM.

Currently, the agent returns answers as plain text without any metadata indicating how the answer was generated. This creates a "black box" experience. Users have no deterministic way to know if the LLM hallucinated a plausible-sounding sales figure or if it actually invoked a backend tool (e.g., executing a DuckDB SQL query) to retrieve factual data.

To bridge this trust gap, we must implement a **Data Queried Flag** (also known as a Grounding Flag or Citation Flag). This serves as the only verifiable proof to the end-user that the agent's response is mathematically grounded in the company's real database.

## Market & Competitor Analysis

Transparency and Auditability are standard features in enterprise LLM products:

- **Perplexity AI / Microsoft Copilot:** Always display citations (e.g., `[1]`, `[2]`) or badges indicating exactly which search results or databases were accessed to formulate the answer.
- **ChatGPT Advanced Data Analysis:** Shows an expandable `[>_ Analyzed]` badge when it writes and executes Python code, proving to the user that a computation actually occurred.
- By lacking a similar verification mechanism, our application shifts the burden of trust entirely onto the user, which is an unacceptable UX pattern for financial/sales data.

## Ideation Results

**1. Idea Name: Data Queried Boolean Flag**

- **Problem Statement:** Users cannot distinguish between an LLM's conversational memory (potential hallucination) and grounded database facts.
- **Proposed Solution:** Modify the orchestration layer (LangChain/LangGraph) to track if any tool was successfully executed during a conversational turn. Append a `data_queried: bool` field to the API's response DTO. The frontend will use this flag to render a "Data Verified" checkmark badge beneath the message.
- **Inspiration/Evidence:** Minimal viable transparency pattern.

**2. Idea Name: Transparent Thought Process (Tool Call Tracing)**

- **Problem Statement:** A simple boolean flag doesn't tell the user *how* the data was fetched.
- **Proposed Solution:** Instead of a boolean, return an array of `tools_used` containing the name of the tool, the SQL query executed, and the raw numerical result. The frontend displays an expandable "View execution logic" accordion.
- **Inspiration/Evidence:** ChatGPT Advanced Data Analysis UX.

**3. Idea Name: Strict LLM Fallback Block**

- **Problem Statement:** The LLM might answer data questions without querying the database.
- **Proposed Solution:** Inject a system prompt rule that forces the LLM to reply with a hardcoded error if it tries to answer a numerical question without using a tool.
- **Inspiration/Evidence:** Restrictive agentic rails.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Data Queried Boolean Flag** | 5 | 5 | 5 | 2 | 2 | **23** |
| Transparent Thought Process (Tool Tracing) | 5 | 5 | 5 | 4 | 3 | **20** |
| Strict LLM Fallback Block | 2 | 2 | 3 | 3 | 5 | **9** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement Data Queried Boolean Flag**

We must implement the `data_queried` flag immediately to provide verifiable grounding for the agent's responses.

- **Tradeoff Analysis:** We are opting for the simpler boolean flag first (Idea 1) rather than exposing the full SQL thought process (Idea 2). Exposing raw SQL to business users might cause confusion or intimidation, whereas a simple "✅ Baseado em dados reais" badge builds trust instantly with low engineering effort. We can iterate towards Idea 2 in future releases if power users request auditability.
- **Recommended Sequencing & Scope:**
  1. **Update DTOs:** Add `data_queried: bool = False` to the `ChatResponseDTO`.
  2. **Orchestrator Tracking:** In `sales_agent.py`, inspect the LangChain/LangGraph execution trace. If the intermediate steps contain any `ToolMessage` or successful tool invocation, toggle `data_queried = True`.
  3. **Frontend Implementation:** Update the Vanilla JS web chat to check for `data_queried`. If true, append a UI badge (e.g., a green checkmark and "Dados Verificados") to the chat bubble.

## Parking Lot

- **Transparent Thought Process (Tool Tracing):** Highly recommended for "v2.0" as an expandable debug view for advanced users.
- **Strict LLM Fallback Block:** Discarded. LLMs are notoriously bad at adhering to negative constraints ("never answer unless..."), and this usually leads to degraded conversational flow.
