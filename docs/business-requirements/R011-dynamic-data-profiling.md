# PRD: Dynamic Data Profiling and Context Injection

## Summary

Origin: [PS011-dynamic-data-profiling.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS011-dynamic-data-profiling.md), Recommendation: Top Recommendation (Implement Dynamic Profiling at Startup).

The **Sales Data Analysis Agent** currently relies on a static, hardcoded system prompt data dictionary to understand table schemas and query semantics. Real-world sales datasets frequently exhibit anomalies, non-standard conventions, and domain quirks—such as storing pseudo-null text representations like `'None'`, `'N/A'`, or `'null'` instead of native SQL `NULL`s, or containing invariant columns with constant values across all rows.

When an LLM operates under static assumptions that deviate from the actual dataset shape, it generates syntactically valid but semantically defective queries (e.g., filtering with `promotion_type IS NULL` when the data actually contains the string `'None'`), leading to false 0-value reports and user-facing hallucinations.

This PRD specifies the transition to a **Dynamic Data Profiling & Context Injection** architecture. At application initialization, a dedicated profiler utility (`DatasetProfiler`) executes lightweight metadata inspection queries against DuckDB to discover data distribution characteristics, sentinel null values, constant fields, and temporal boundaries. These empirical findings are dynamically compiled into a high-signal context block and injected into the agent's `SYSTEM_PROMPT` at runtime, ensuring the agent adapts seamlessly to the true data reality without mutating raw source datasets.

## Functional Requirements

- **PRD01 (Automated Startup Metadata Profiling):** The system must execute automated, read-only metadata profiling on DuckDB during application initialization.
- **PRD02 (Pseudo-Null & Sentinel Value Detection):** The profiler must inspect categorical and text columns (specifically `promotion_type`) to detect whether missing or baseline records are encoded using string literals (such as `'None'`, `'N/A'`, `'null'`, or empty strings `''`) or standard SQL `NULL`s.
- **PRD03 (Invariant & Constant Column Discovery):** The profiler must identify columns exhibiting low cardinality or uniform constant values across the entire dataset (e.g., a static `service_level = 0.95`) and document their invariant nature.
- **PRD04 (Temporal Span & Cardinality Grounding):** The profiler must capture dataset boundaries, including:
  - Total records count.
  - Date boundaries (minimum date and maximum date formatted as `DD/MM/YYYY`).
  - Distinct count of `product_id`s and `local` distribution hubs.
- **PRD05 (Dynamic Prompt Context Synthesis & Injection):** The system must synthesize the profiling observations into a standardized Markdown block (`### DYNAMIC DATA INSIGHTS:`) and dynamically inject it into the `SYSTEM_PROMPT` during `SalesAgent` instantiation.
- **PRD06 (Zero-Mutation Data Lineage Preservation):** The profiling mechanism must operate in strict read-only mode, never executing `UPDATE`, `ALTER`, or cleansing mutations against the raw DuckDB database or source files.
- **PRD07 (In-Memory Profiling Caching & Fallback):** The generated profile must be computed once at startup and cached in memory for the container lifecycle. In the event of a profiling query failure, the system must log a warning and fall back gracefully to the default static prompt without crashing.

## Non-Functional Requirements

- **Startup Performance & Latency:** The entire profiling inspection query suite must execute in sub-100ms latency on startup for datasets up to 1,000,000 records.
- **LLM Token Efficiency:** The dynamic insights block injected into the system prompt must be concise, structured, and high-signal (consuming fewer than 150 tokens) to prevent context bloat.
- **Reliability & Fault Tolerance:** Any transient error during schema profiling must be captured gracefully, preventing application boot failures.
- **Clean Architecture Decoupling:** Profiling logic must be encapsulated within the persistence/adapter layer (`DatasetProfiler`), maintaining clear separation from application use cases and domain models.

## Business Rules

- **BR01 (Raw Data Immutability):** The application must adapt to the dataset's actual structure through prompt enrichment rather than transforming or modifying raw database records.
- **BR02 (Explicit Sentinel Null Guidance):** When a column contains string sentinel values like `'None'`, the injected prompt must explicitly instruct the LLM to write queries using equality matches (`WHERE promotion_type = 'None'`) rather than SQL null checks (`IS NULL`).
- **BR03 (Authoritative Boundary Grounding):** Profiled temporal boundaries and entity lists serve as ground-truth bounds, empowering the LLM to answer boundary queries immediately without executing redundant database lookups.
- **BR04 (Deterministic Startup Profiling):** Profiling must run deterministically on every container boot, ensuring any updated dataset mounted into the container is automatically profiled on next restart.

## Critical Data (Conceptual)

- **Dataset Profile Metadata:**
  - `total_records`: Integer count of total rows.
  - `min_date` and `max_date`: String representations of the historical date range.
  - `distinct_products`: List or count of unique product identifiers.
  - `distinct_locations`: List of distribution warehouses.
- **Data Distribution Insights:**
  - `null_representations`: Map of column names to identified pseudo-null string formats.
  - `constant_columns`: Map of column names to static constant values.
- **Injected Prompt Fragment:** Formatted Markdown text segment containing the empirical rules dynamically appended to the agent's system prompt.

## User Flow

### Happy Path 1 (Non-Promotional Sales Inquiry with String 'None')

1. The application boots. The `DatasetProfiler` inspects DuckDB and detects that `promotion_type` contains the string `'None'` for regular sales instead of SQL `NULL`.
2. The system formats the dynamic insight: `"- 'promotion_type': Vendas não promocionais utilizam a string 'None' (e não SQL NULL). Utilize WHERE promotion_type = 'None'."`.
3. The dynamic block is injected into `SYSTEM_PROMPT` during `SalesAgent` initialization.
4. The user asks: "Quantas vendas foram realizadas sem promoção?".
5. The AI Agent inspects its dynamic prompt, generates `SELECT COUNT(*) FROM sales_data WHERE promotion_type = 'None'`, and executes the query.
6. The query returns the exact correct count, completely eliminating the false 0-value hallucination.

### Happy Path 2 (Temporal Out-of-Bounds Inquiry)

1. During startup, the profiler discovers the dataset covers exclusively `01/01/2024` to `31/12/2024`.
2. The dynamic prompt injects: `"- Período temporal coberto: 01/01/2024 até 31/12/2024."`.
3. The user asks: "Qual foi o faturamento total em Março de 2025?".
4. The AI Agent recognizes from its context that data for 2025 does not exist and informs the user immediately, saving query latency and preventing hallucinated results.

### Exception Path 1 (Database Profiling Timeout or Locked Table)

1. On container startup, an issue occurs during exploratory profiling queries (e.g., table not yet loaded).
2. `DatasetProfiler` catches the exception and logs `logger.warning("[DATASET_PROFILING] Profiling failed, proceeding with default prompt schema.")`.
3. The application proceeds with the standard static system prompt without interrupting container boot.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | `DatasetProfiler` executes automated profiling queries on startup without altering raw DuckDB records. | Unit and integration test verifying profiler execution and asserting database immutability. |
| AC02 | Profiler detects string sentinel representations (`'None'`, `'N/A'`, `'null'`) in categorical columns like `promotion_type`. | Automated test with dataset containing `'None'` strings asserting correct metadata detection. |
| AC03 | Profiler detects constant/invariant columns (e.g., `service_level = 0.95`) and documents value invariance. | Unit test verifying detection of single-cardinality columns. |
| AC04 | Profiler extracts accurate date bounds (`min_date`, `max_date`) and entity counts (`products`, `locations`). | Metadata assertion test matching extracted bounds against ground-truth table statistics. |
| AC05 | `SalesAgent` dynamically receives the synthesized `### DYNAMIC DATA INSIGHTS` block in its `SYSTEM_PROMPT`. | Agent prompt inspection test validating presence of dynamic insights section. |
| AC06 | Fallback queries on non-promotional data correctly utilize discovered sentinel strings (`WHERE promotion_type = 'None'`). | End-to-end agent query test asserting generated SQL matches discovered sentinel rules. |
| AC07 | Startup profiling completes in under 100ms and gracefully falls back to default prompt on query failure. | Latency benchmark test and error fallback simulation test. |
