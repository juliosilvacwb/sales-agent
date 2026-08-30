# Product Strategy: Deterministic Golden Evals for Analytical AI

## Strategic Context

The **Sales Data Analysis Agent** operates as an intelligent interface between business users and a DuckDB analytical engine. Because Large Language Models (LLMs) are inherently non-deterministic, any update to the system—whether modifying a system prompt, adding a new tool, or changing the underlying LLM provider—introduces the risk of "Prompt Drift." A previously working query (e.g., "What is the total revenue?") might suddenly break if the LLM hallucinates an incorrect SQL syntax or selects the wrong internal tool.

Relying on traditional unit tests is insufficient because they only validate the Python execution layer, bypassing the "brain" of the application (the LLM). To guarantee enterprise-level reliability and ensure that business users always receive mathematically correct answers, we must implement automated AI evaluation testing: **Golden Evals**.

## Market & Competitor Analysis

In the emerging field of **LLMOps**, testing is bifurcated into two patterns:

1. **Generative Evaluation (LLM-as-a-Judge):** Used for subjective tasks (e.g., summarizing text or analyzing sentiment). Requires a secondary LLM to judge the output, which is costly and probabilistically flawed.
2. **Deterministic Evaluation (Exact Match):** Used for Data Analytics and Text-to-SQL agents. The evaluation intercepts the data returned by the database/tool *before* the LLM converts it into conversational text, validating the exact numeric outcome against a hardcoded "Golden" baseline.

Since the core value proposition of our product is exact financial and sales reporting, Deterministic Evals are the absolute industry standard. Competitors offering secure enterprise BI copilots rely strictly on deterministic validation to prove zero-hallucination guarantees on math.

## Ideation Results

**1. Idea Name: Deterministic Golden Evals via CI/CD**

- **Problem Statement:** Prompt changes can silently break the LLM's ability to fetch correct sales numbers.
- **Proposed Solution:** Create a `Golden Dataset` containing complex, edge-case analytical questions mapped to their exact, unarguable numerical results. Build an automated test suite that asks the agent these questions and intercepts the internal tool execution to assert that the returned `float` or `int` matches the golden number perfectly, independent of the agent's final conversational phrasing.
- **Inspiration/Evidence:** Industry-standard Text-to-SQL benchmarking (like Spider or BIRD datasets).

**2. Idea Name: LLM-as-a-Judge Evaluation**

- **Problem Statement:** Need to evaluate if the agent's final message is polite and factually correct.
- **Proposed Solution:** Use an advanced model like GPT-4 to read the agent's final conversational output and judge if the numbers presented are correct based on a baseline.
- **Inspiration/Evidence:** Generative evaluation frameworks (LangSmith, DeepEval).

**3. Idea Name: Human-in-the-Loop (HITL) Manual QA**

- **Problem Statement:** Need to ensure the bot answers correctly before production.
- **Proposed Solution:** A human data analyst manually runs 50 queries in a staging chat interface before every release.
- **Inspiration/Evidence:** Legacy software QA practices.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic Golden Evals** | 5 | 5 | 5 | 3 | 4 | **22** |
| LLM-as-a-Judge Evaluation | 3 | 3 | 2 | 2 | 2 | **12** |
| Human-in-the-Loop Manual QA | 2 | 4 | 1 | 1 | 1 | **9** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement Deterministic Golden Evals via CI/CD**

We must implement a deterministic evaluation pipeline to act as a regression safety net for all future AI prompt and tool engineering.

- **Tradeoff Analysis:** We consciously reject LLM-as-a-Judge for this specific feature because evaluating deterministic math using a non-deterministic judge adds unnecessary cost (token usage), latency, and risk of false negatives/positives. Deterministic Evals are cheaper, 100% accurate, and perfectly suited for analytical data validation.
- **Recommended Sequencing & Scope:**
  1. **Dataset Creation:** Define a `golden_dataset.json` containing ~10 complex business queries (e.g., aggregations, filtering by location, elasticity). Each entry must include the `question` and the `expected_result`.
  2. **Eval Runner:** Create a test script (e.g., `tests/evals/test_golden_evals.py`) that initializes the `SalesAgent`, loops through the dataset, inputs the question, and validates the intercepted tool result against the `expected_result`.
  3. **CI/CD Integration (Smoke Evals):** Integrate this script into the GitHub Actions pipeline defined in PS007. It must run on every Pull Request to `master` using a cost-effective LLM (e.g., `gpt-4o-mini`) to prevent broken prompts from ever reaching production.

## Parking Lot

- **LLM-as-a-Judge Evaluation:** Highly relevant for the future if we add subjective features to the agent (e.g., "Analyze the sentiment of customer reviews"), but inappropriate for strict mathematical sales data.
- **Human-in-the-Loop Manual QA:** Completely unscalable and discarded for the core deployment pipeline.
