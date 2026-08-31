<!-- markdownlint-disable MD013 -->
# T011: Dynamic Data Profiling and Context Injection

## PRD Reference

- **PRD:** [R011-dynamic-data-profiling.md](../business-requirements/R011-dynamic-data-profiling.md)
- **Test Coverage:** [TEST011-dynamic-data-profiling.md](../tests/TEST011-dynamic-data-profiling.md)
- **Security Audit:** [S011-dynamic-data-profiling.md](../security/S011-dynamic-data-profiling.md)

## Technical Goal

Transition the Sales Data Analysis Agent from a static prompt schema to a dynamic, dataset-aware context. At application startup, a lightweight `DatasetProfiler` will query the DuckDB instance to detect sentinel string nulls (e.g., `'None'`), invariant columns, and temporal bounds. These empirical findings will be formatted into a `### DYNAMIC DATA INSIGHTS` block and injected into the agent's `SYSTEM_PROMPT`, eliminating false 0-value hallucinations caused by rigid LLM assumptions without mutating the raw database.

## Architecture Decisions (ADRs)

### ADR-01: Read-Only Empirical Profiling

- **Decision:** The profiler will exclusively execute `SELECT` queries to derive insights. It will not execute `ALTER TABLE`, `UPDATE`, or any cleansing mutations on the raw data.
- **Rationale:** Strict adherence to BR01 (Raw Data Immutability). The agent must adapt its queries to the dataset's reality, rather than forcing the dataset to conform to the agent's assumptions.

### ADR-02: Port-Driven Profiling Abstraction

- **Decision:** Profiling will be modeled as a capability on the Outbound Database Port (`SalesDataPort.profile_dataset() -> DatasetProfile`). The DuckDB adapter will implement the specific SQL profiling queries.
- **Rationale:** Maintains Hexagonal boundary integrity. The orchestration layer (bootstrap or agent factory) requests the profile via the interface, remaining agnostic to DuckDB-specific query syntax.

### ADR-03: Startup Caching and Graceful Fallback

- **Decision:** The profile will be executed exactly once per application boot/container start and cached in memory. If the profiling queries fail (e.g., table not ready, syntax error), the exception will be swallowed, logged as a warning, and the agent will boot using the standard static prompt.
- **Rationale:** Prevents application startup crashes (NFR: Reliability & Fault Tolerance) while optimizing latency since the underlying dataset structure is static for the lifespan of the session.

## Security and Reliability

### Security Mitigations

- **Query Injection Prevention:** Profiling queries will be hardcoded structural queries without user input, eliminating SQL injection vectors during the boot phase.

### Performance

- **DuckDB Profiling Execution:** DuckDB is highly optimized for analytical scans. The profiling queries will utilize `MIN()`, `MAX()`, `COUNT(DISTINCT)`, and `GROUP BY` on a single scan where possible to ensure sub-100ms execution times for up to 1M records.

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Domain Models and Port Interfaces (Zero Dependencies)

#### Phase 1 tasks (all parallel-safe)

- [COMPLETED] Task 001 - [Domain-Model]: Create `DatasetProfile` and `DataInsights` models (Depends On: —)
- [COMPLETED] Task 002 - [Port-Out]: Update `SalesDataPort` with `profile_dataset` interface (Depends On: Task 001)

### 🟡 Phase 2 — Persistence Implementation (Depends on Phase 1)

#### Phase 2 tasks (all parallel-safe)

- [COMPLETED] Task 003 - [Adapter-Persistence]: Implement DuckDB `DatasetProfiler` logic (Depends On: Task 002)

### 🟢 Phase 3 — Agent Orchestration and Injection (Depends on Phase 2)

#### Phase 3 tasks (all parallel-safe)

- [COMPLETED] Task 004 - [Adapter-Web]: Update Agent Factory to inject Dynamic Insights block (Depends On: Task 003)
- [COMPLETED] Task 005 - [Test-Integration]: Implement E2E tests for dynamic prompt adaptation (Depends On: Task 004)

## Task Detailing (Summary Tasks)

### Task 001 - [Domain-Model]: Create DatasetProfile and DataInsights models

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 002
- **Objective:** Define the structure for the empirical profiling results.
- **Files/Path:** `src/domain/model/dataset_profile.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Create a dataclass/Pydantic model `DatasetProfile` containing: `total_records`, `min_date`, `max_date`, `distinct_products`, `distinct_locations`.
  - Add fields for `null_representations` (dict mapping column to string nulls) and `constant_columns` (dict mapping column to its constant value).
  - Implement a method `to_markdown_block() -> str` that formats the object into the `### DYNAMIC DATA INSIGHTS:` text block.

---

### Task 002 - [Port-Out]: Update SalesDataPort with profile_dataset interface

- **Phase:** 1
- **Depends On:** Task 001
- **Parallel With:** Task 001
- **Objective:** Expose the profiling capability to the application boundary.
- **Files/Path:** `src/application/port/outbound/sales_data_port.py`
- **Reuse:** Existing `SalesDataPort`.
- **Technical Acceptance Criteria:**
  - Add `def profile_dataset(self) -> DatasetProfile:` to the abstract interface.

---

### Task 003 - [Adapter-Persistence]: Implement DuckDB DatasetProfiler logic

- **Phase:** 2
- **Depends On:** Task 002
- **Parallel With:** —
- **Objective:** Execute the high-speed structural queries on DuckDB to populate the profile.
- **Files/Path:** `src/adapter/outbound/persistence/duckdb_adapter.py`
- **Reuse:** Existing DuckDB connection mechanics.
- **Technical Acceptance Criteria:**
  - Implement `profile_dataset`.
  - Execute a query to get global stats: `SELECT COUNT(*), MIN(date), MAX(date), COUNT(DISTINCT product_id), COUNT(DISTINCT local) FROM sales_data`.
  - Execute an exploratory query to detect sentinel strings in text columns: e.g., checking if `promotion_type` contains `'None'`, `'N/A'`, or `''`.
  - Execute an exploratory query to find invariant columns (where `MIN(col) == MAX(col)`).
  - Wrap the entire operation in a `try/except Exception` block, returning a default empty/static profile if it fails, ensuring the app boot does not crash.

---

### Task 004 - [Adapter-Web]: Update Agent Factory to inject Dynamic Insights

- **Phase:** 3
- **Depends On:** Task 003
- **Parallel With:** —
- **Objective:** Request the profile on startup and inject it into the static `SYSTEM_PROMPT`.
- **Files/Path:** `src/adapter/inbound/llm/sales_agent.py` (and relevant bootstrap factories)
- **Reuse:** Existing `SYSTEM_PROMPT`.
- **Technical Acceptance Criteria:**
  - In the factory or orchestrator that creates `SalesAgent`, call `sales_data_port.profile_dataset()`.
  - Retrieve the markdown string: `insights_text = profile.to_markdown_block()`.
  - Append `insights_text` to the base `SYSTEM_PROMPT`.
  - Pass the augmented system prompt to the `create_agent` / AgentExecutor setup.

---

### Task 005 - [Test-Integration]: Implement E2E tests for dynamic prompt adaptation

- **Phase:** 3
- **Depends On:** Task 004
- **Parallel With:** —
- **Objective:** Verify that the agent correctly parses the injected insights and modifies its SQL generation behavior.
- **Files/Path:** `tests/integration/test_dynamic_profiling.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:**
  - Seed a test DuckDB database where `promotion_type` uses `'None'` instead of `NULL`, and `service_level` is a constant `0.99`.
  - Boot the agent. Verify the prompt injection occurred.
  - Ask the agent a question: "Quantas vendas não tiveram promoção?".
  - Intercept the SQL generated by the fallback tool and assert that it contains `WHERE promotion_type = 'None'` rather than `IS NULL`.
  - Verify that if the profile fails (e.g. by dropping the table temporarily before boot), the agent boots safely with the default prompt.

## Verification Plan

### Automated Tests

- Unit test for `to_markdown_block` output format.
- Integration tests verifying DuckDB adapter correctly identifies sentinels and boundaries.
- Full E2E test verifying SQL behavioral change based on the prompt.

### Manual Verification

- Boot the application against the real dataset.
- Print the generated `SYSTEM_PROMPT` to the console/logs and visually inspect the `### DYNAMIC DATA INSIGHTS:` block to confirm it accurately describes the dataset's anomalies.
- Ask the agent a boundary question (e.g., "Temos vendas de 2025?") and observe it answering deterministically without executing a SQL query.
