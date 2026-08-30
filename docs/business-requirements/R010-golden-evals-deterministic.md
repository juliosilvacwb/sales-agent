# PRD: Deterministic Golden Evals for Analytical AI

## Summary

Origin: [PS010-golden-evals-deterministic.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS010-golden-evals-deterministic.md), Recommendation: Top Recommendation (Implement Deterministic Golden Evals via CI/CD).

The **Sales Data Analysis Agent** functions as an intelligent analytical assistant over a DuckDB database. While traditional unit tests validate Python code paths, they cannot evaluate the non-deterministic reasoning of the LLM. Any modification to system prompts, tool schemas, or underlying model providers introduces the risk of "Prompt Drift" and mathematical hallucinations, where previously working business queries silently return incorrect sales figures.

Subjective evaluation techniques (such as LLM-as-a-Judge) are costly, introduce probabilistic inconsistency, and are ill-suited for strict financial and analytical reporting where answers must be mathematically exact.

This PRD specifies the requirements for an automated, **Deterministic Golden Evaluation (Golden Evals)** framework. A curated dataset (`golden_dataset.json`) maps canonical business queries to unarguable ground-truth numerical outcomes. An automated evaluation runner executes the agent against this benchmark, intercepts the structured data returned by internal tools prior to natural language rendering, and asserts exact mathematical matches. Integrated directly into the CI/CD pipeline, this framework guarantees zero mathematical regression across releases.

## Functional Requirements

- **PRD01 (Curated Golden Analytical Dataset):** The system must provide a version-controlled benchmark dataset (`tests/evals/golden_dataset.json`) containing canonical business queries covering key analytical dimensions: revenue aggregations, volume comparisons, promotional impact, service level bottlenecks, seasonality, and price elasticity.
- **PRD02 (Ground-Truth Structured Schema):** Each golden dataset entry must define:
  - `eval_id`: Unique identifier (e.g., `EVAL_001_TOTAL_REVENUE`).
  - `category`: Analytical domain classification.
  - `question`: Natural language user prompt.
  - `expected_tool`: Name of the tool the agent is expected to invoke.
  - `expected_metrics`: Exact ground-truth numerical values, scalar metrics, or structured data records.
- **PRD03 (Intermediate Tool Output Interception):** The evaluation harness must intercept the raw data payload emitted by the domain or fallback tools during agent execution, validating the underlying data before the LLM synthesizes it into natural language conversational text.
- **PRD04 (Deterministic Assertion Engine with Float Tolerance):** The assertion engine must validate numerical metrics with configurable floating-point tolerances (e.g., `abs_tol=0.01` or `rel_tol=1e-3`) to accommodate standard rounding variations while strictly rejecting mathematical divergence.
- **PRD05 (Automated CI/CD Quality Gate):** The evaluation suite must be integrated into GitHub Actions CI (`.github/workflows/ci-cd.yml` or dedicated eval workflow), running automatically on Pull Requests to `master` and halting the pipeline if any golden evaluation fails.
- **PRD06 (Structured Diagnostic Reporting):** When a golden evaluation fails, the runner must output a detailed diagnostic report detailing the query, expected tool vs. invoked tool, expected numerical payload vs. actual received payload, and the specific delta.
- **PRD07 (Resilient API Execution & Retry Logic):** The evaluation runner must handle transient LLM provider rate limits and network glitches with automatic exponential backoff retries to prevent flaky CI failures.

## Non-Functional Requirements

- **Zero Mathematical Hallucination Guarantee:** The evaluation framework must provide 100% deterministic mathematical verification for all benchmark business questions.
- **Evaluation Speed & Latency:** The standard benchmark suite (10 to 15 golden cases) must execute completely in under 60 seconds on CI runners.
- **Cost Efficiency:** Golden evaluations must be executable with cost-effective model tiers (e.g., `gpt-4o-mini`), keeping operational CI costs minimal per pull request.
- **Data Isolation & Reproducibility:** Evaluations must run against a fixed, reproducible analytical dataset fixture to guarantee repeatable results across all development and CI environments.
- **Declarative Extensibility:** New evaluation test cases must be addable directly to `golden_dataset.json` without requiring modifications to the Python test harness code.

## Business Rules

- **BR01 (Zero Tolerance for Mathematical Regression):** All test cases in `golden_dataset.json` must achieve a 100% pass rate for a Pull Request to merge into `master`.
- **BR02 (Pre-Generation Interception):** Assertions must be performed directly against the structured data returned by tools, preventing natural language phrasing variations from causing false positives or negatives.
- **BR03 (Strict Tool Routing Compliance):** Queries designed for specific Domain Tools must not fall back to `SecuredSQLQueryTool` when a domain tool is directly applicable.
- **BR04 (Precision Standards):** Monetary sums and unit prices must match within `0.01` precision; percentages and elasticity coefficients must match within `0.001` precision.

## Critical Data (Conceptual)

- **Golden Benchmark Entry:**
  - `eval_id` (string).
  - `category` (string: `REVENUE`, `PROMOTION`, `LOGISTICS`, `SEASONALITY`, `ELASTICITY`, `AD_HOC_SQL`).
  - `question` (string).
  - `expected_tool` (string).
  - `expected_metrics` (map of metric keys to numeric/string values).
- **Evaluation Execution Metrics:**
  - Total evaluations executed, passed, failed, and execution duration.
  - LLM token usage and estimated run cost.
- **Diagnostic Trace Log:** Detailed mismatch log showing expected vs actual values, tool invocation parameters, and intermediate agent reasoning steps.

## User Flow

### Happy Path (Pull Request Verification via Golden Evals)

1. A developer modifies a system prompt or refactors an internal tool.
2. The developer opens a Pull Request against `master`.
3. GitHub Actions CI triggers the `golden-evals` job.
4. The evaluation harness loads `golden_dataset.json` and spins up the `SalesAgent` with the test dataset fixture.
5. The runner iterates through all golden benchmark queries, sending each question to the agent.
6. The interceptor captures each tool execution, asserting tool selection and verifying returned numerical values against `expected_metrics`.
7. All test cases match with 100% precision.
8. The GitHub Actions job passes, marking the PR green for merge.

### Exception Path 1 (Prompt Drift Causes Incorrect Tool Routing)

1. A prompt change causes the LLM to route `EVAL_001_TOTAL_REVENUE` to `SecuredSQLQueryTool` instead of the domain tool `get_total_sales_in_period`.
2. The eval runner intercepts the tool execution and detects `actual_tool='secured_sql_query'` instead of `expected_tool='get_total_sales_in_period'`.
3. The runner flags a routing violation and fails the test.
4. The CI build halts, providing clear diagnostic logs so the developer can refine the system prompt.

### Exception Path 2 (Calculation Regression / Mathematical Inaccuracy)

1. A modification in price elasticity calculation logic alters coefficient rounding or baseline calculation.
2. The eval runner executes `EVAL_006_PRICE_ELASTICITY`.
3. The intercepted elasticity coefficient is `-1.45`, but the ground-truth golden expectation is `-2.00`.
4. The assertion fails with `AssertionError: Metric 'elasticity_coefficient' mismatch (Actual: -1.45, Expected: -2.00)`.
5. The CI job fails, preventing a mathematically flawed deployment from reaching production.

### Exception Path 3 (Transient LLM API Rate Limit / Timeout)

1. During CI evaluation, an LLM API request encounters a transient `429 Too Many Requests` or `503 Service Unavailable`.
2. The evaluation harness catches the rate limit exception and applies exponential backoff with jitter.
3. The request retries and succeeds, allowing the evaluation suite to complete without flaky build failures.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | Curated `golden_dataset.json` is created with minimum 10 canonical test cases covering core analytical queries. | Dataset schema inspection and coverage verification across all 10 domain capabilities. |
| AC02 | Evaluation test runner (`test_golden_evals.py`) executes queries against `SalesAgent` and intercepts tool payloads. | Automated pytest execution verifying tool interception and payload assertions. |
| AC03 | Numeric assertions enforce float tolerance (`abs_tol=0.01` / `rel_tol=1e-3`) for revenue, quantities, and coefficients. | Unit tests validating tolerance bounds on mock values. |
| AC04 | Tool routing assertions verify that queries invoke the specific expected tool (`expected_tool`). | Evaluation run verifying rejection when tool selection deviates. |
| AC05 | Runner produces structured failure reports detailing mismatch metrics, expected values, and observed values. | Test assertion on diagnostic log formatting upon intentional assertion failure. |
| AC06 | Golden evals suite is integrated into CI workflow (`.github/workflows/ci-cd.yml`) as a PR gating check. | Workflow definition check and GitHub Actions dry-run execution. |
| AC07 | Entire golden eval suite executes in under 60 seconds against a standard test dataset fixture. | Benchmark execution timing in automated test environment. |
