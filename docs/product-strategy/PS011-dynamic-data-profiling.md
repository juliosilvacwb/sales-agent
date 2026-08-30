# Product Strategy: Dynamic Data Profiling & Context Injection

## Strategic Context

The **Sales Data Analysis Agent** currently relies on a static, hardcoded `SYSTEM_PROMPT` to understand the database schema and data semantics (the Data Dictionary). However, raw analytical datasets often contain unexpected characteristics—such as using the string `"None"` instead of a proper SQL `NULL`, or containing columns where the value never varies (e.g., a constant `service_level`).

When the LLM operates under false assumptions provided by a hardcoded prompt, it generates syntacticamente correct but semantically flawed SQL queries, resulting in hallucinations (e.g., reporting 0 sales without promotions because it filtered by `IS NULL` instead of `= 'None'`).

To eliminate these blind spots and elevate the agent to a true "Data Engineering" level, the system must dynamically profile the dataset upon initialization and inject the real-world data distribution rules directly into the LLM's context window.

## Market & Competitor Analysis

In modern Data-Aware AI architectures (like advanced RAG for structured data), the system never trusts the nominal schema blindly.

- **Dynamic Context Injection:** Best-in-class Text-to-SQL solutions run descriptive statistics (min, max, unique counts, null checks) on the target tables before prompting the LLM.
- **Data over Code:** Instead of transforming the entire dataset (ETL) to match the prompt's assumptions (which can be slow and expensive), the application transforms the *prompt* to match the reality of the data. This drastically improves the LLM's query accuracy and contextual awareness.

## Ideation Results

**1. Idea Name: Dynamic Profiling at Startup**

- **Problem Statement:** Hardcoded data dictionaries lead to incorrect SQL generation when the real data shape deviates from the prompt's assumptions.
- **Proposed Solution:** Introduce a `DatasetProfiler` service. During application startup, this service runs lightweight metadata queries against DuckDB (e.g., checking distinct values, finding non-standard null representations like "None"). It formats these insights into a short text summary and dynamically appends it to the `SYSTEM_PROMPT`. **The underlying data is never mutated.**
- **Inspiration/Evidence:** Industry-standard Data-Aware Prompting and Data Quality (DQ) profiling.

**2. Idea Name: Static Prompt Correction**

- **Problem Statement:** The current prompt has incorrect assumptions about `promotion_type`.
- **Proposed Solution:** Manually edit the `SYSTEM_PROMPT` string in the code to hardcode the new rules discovered by the evaluator (e.g., typing "Use 'None' instead of NULL").
- **Inspiration/Evidence:** Quick fixes (Technical Debt).

**3. Idea Name: Pre-processing ETL (Data Cleansing)**

- **Problem Statement:** The data is dirty (uses "None" instead of NULL).
- **Proposed Solution:** Write a Python script to iterate through the CSV/DuckDB table and forcefully replace all `"None"` strings with actual `NULL` values so it matches the original prompt.
- **Inspiration/Evidence:** Traditional Data Engineering pipelines.

## Prioritization Matrix

| Idea | Business Value (1-5) | User Impact (1-5) | Strategic Alignment (1-5) | Effort (1-5, lower=better) | Risk (1-5, lower=better) | Weighted Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dynamic Profiling at Startup** | 5 | 5 | 5 | 3 | 4 | **22** |
| Pre-processing ETL (Data Cleansing) | 4 | 4 | 3 | 2 | 3 | **16** |
| Static Prompt Correction | 2 | 2 | 1 | 5 | 1 | **11** |

*Note: Effort and Risk are inverted for scoring (lower effort/risk = higher score).*

## Recommendations

**Top Recommendation: Implement Dynamic Profiling at Startup**

We must implement Dynamic Context Injection. The application should adapt to the data, not force the data to adapt to the application.

- **Tradeoff Analysis:** We are explicitly choosing *not* to mutate the raw data (rejecting the ETL approach) to preserve data lineage and minimize startup latency. The tradeoff is that the LLM prompt becomes slightly larger (consuming a few more tokens), but this guarantees absolute contextual accuracy regardless of what dataset is loaded.
- **Recommended Sequencing & Scope:**
  1. Create a `DatasetProfiler` utility within the `DuckDbSalesAdapter`.
  2. Implement a `profile_schema()` method that executes automated exploratory queries:
     - Find columns with only 1 distinct value (Constants).
     - Find columns that use string literals like `"None"`, `"N/A"`, or `"NaN"` instead of SQL `NULL`.
  3. Format the output into a string block (e.g., `### DYNAMIC DATA INSIGHTS: \n- 'promotion_type' uses the string 'None' to represent missing values.\n- 'service_level' is a constant 0.95.`).
  4. Inject this block into the `SYSTEM_PROMPT` during the `SalesAgent` initialization.

## Parking Lot

- **Pre-processing ETL (Data Cleansing):** While data cleansing is a valid discipline, it is better suited for an upstream Data Pipeline (like dbt or Airflow) rather than being hardcoded into the AI Agent's runtime.
- **Static Prompt Correction:** Discarded. It is fragile and breaks immediately if a new dataset with different quirks is loaded.
