# Architecture Specification: Analytical Engine Scalability (T003)

## PRD Reference

- **PRD:** [R003-analytical-engine-scalability.md](../business-requirements/R003-analytical-engine-scalability.md)
- **Test Coverage:** [TEST003-analytical-engine-scalability.md](../tests/TEST003-analytical-engine-scalability.md)
- **Security Audit:** [S003-analytical-engine-scalability.md](../security/S003-analytical-engine-scalability.md)



## Technical Goal

Migrate in-memory Python calculations to DuckDB SQL pushdown aggregations to ensure the system scales efficiently for datasets up to 50M+ records without Out-of-Memory (OOM) errors and in sub-second latency.

## Architecture Decisions (ADRs)

- **ADR-001: SQL Pushdown for Aggregations:** Evaluated maintaining logic in Python (scaling via Pandas/Dask) vs pushing down to DuckDB. Chose DuckDB SQL pushdown because the data is already inside DuckDB, and its columnar vectorized engine provides sub-second latency for these specific analytical workloads without transferring large datasets over the memory bus.
- **ADR-002: Refactoring Metrics Services to accept Aggregated Data:** Evaluated injecting the Data Port directly into Domain Services vs keeping Domain Services pure. Chose to keep Domain Services pure to adhere strictly to the Hexagonal Architecture rules (Phase 1 cannot depend on Phase 2). The `SalesMetricsApplicationService` (Use Case) will call the Output Port (`SalesDataPort`) to fetch aggregated DTOs, and then pass these lightweight payloads to the Domain Services (`BasicMetricsService`, `AdvancedMetricsService`) to apply final business rules and construct the result objects.

## Security & Reliability

- **Memory Safety:** By eliminating the usage of `get_all_sales()`, the application heap is protected from OOM crashes when processing large datasets.
- **SQL Injection Mitigation:** All DuckDB queries must use parameterized SQL statements to maintain the existing security posture.

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Domain Core

- [COMPLETED] Task 001 - [Domain-Model]: Create aggregated data structures (e.g., `ProductAggregation`, `LocationAggregation`) (Depends On: —)
- [COMPLETED] Task 002 - [Domain-Service]: Refactor `BasicMetricsService` to accept aggregated data structures (Depends On: Task 001)
- [COMPLETED] Task 003 - [Domain-Service]: Refactor `AdvancedMetricsService` to accept aggregated data structures (Depends On: Task 001)

### 🟡 Phase 2 — Ports & Use Cases

- [COMPLETED] Task 004 - [Port-Out]: Refactor `SalesDataPort` interface to include specific analytical methods (Depends On: Task 001)
- [COMPLETED] Task 005 - [UseCase]: Refactor `SalesMetricsApplicationService` to orchestrate calls between port and services (Depends On: Task 002, Task 003, Task 004)

### 🟢 Phase 3 — Adapters

- [COMPLETED] Task 006 - [Adapter-Persistence]: Implement the new aggregation methods in `DuckDbSalesAdapter` using SQL (Depends On: Task 004)
- [COMPLETED] Task 007 - [Adapter-Persistence]: Deprecate or remove `get_all_sales()` to prevent memory risks (Depends On: Task 006)
- [COMPLETED] Task 008 - [Test-Integration]: Implement end-to-end tests ensuring result parity with legacy Python logic (Depends On: Task 005, Task 006)




## Task Detailing (Summary Tasks)

### Task 001 - [Domain-Model]: Create aggregated data structures

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** —
- **Objective:** Create lightweight data classes (e.g., dataclasses in `src/domain/model/`) to represent intermediate aggregated results from the database (e.g., `TopSellingProductData`, `LocationSalesData`, etc.).
- **Files/Path:** `src/domain/model/aggregation_models.py` (New File)
- **Reuse:** None.
- **Technical Acceptance Criteria:** Pure POJOs/dataclasses with zero framework dependencies.

### Task 002 - [Domain-Service]: Refactor BasicMetricsService

- **Phase:** 1
- **Depends On:** Task 001
- **Parallel With:** Task 003
- **Objective:** Change method signatures to accept the new aggregated data structures instead of `Sequence[SaleRecord]`.
- **Files/Path:** `src/domain/service/basic_metrics_service.py`
- **Reuse:** Existing `Result` models (`TopSellingProductResult`, etc.).
- **Technical Acceptance Criteria:** Methods must build final result objects using the pre-calculated aggregated data without iterating over raw sales records. Unit tests updated.

### Task 003 - [Domain-Service]: Refactor AdvancedMetricsService

- **Phase:** 1
- **Depends On:** Task 001
- **Parallel With:** Task 002
- **Objective:** Change method signatures to accept aggregated data structures instead of `Sequence[SaleRecord]`.
- **Files/Path:** `src/domain/service/advanced_metrics_service.py`
- **Reuse:** Existing `Result` models.
- **Technical Acceptance Criteria:** Logic is simplified to pure business formatting and final calculation (if any) based on aggregated data. Unit tests updated.

### Task 004 - [Port-Out]: Refactor SalesDataPort interface

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** —
- **Objective:** Add abstract methods for SQL aggregations (e.g., `aggregate_sales_by_product()`, `aggregate_sales_by_location()`).
- **Files/Path:** `src/application/port/outbound/sales_data_port.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:** Interface exposes clear, domain-aligned aggregation methods returning the structures defined in Task 001.

### Task 005 - [UseCase]: Refactor SalesMetricsApplicationService

- **Phase:** 2
- **Depends On:** Task 002, Task 003, Task 004
- **Parallel With:** —
- **Objective:** Update the application service to fetch aggregated data from `SalesDataPort` and pass it to the Domain Services.
- **Files/Path:** `src/application/service/sales_metrics_service.py`
- **Reuse:** `SalesDataPort`, `BasicMetricsService`, `AdvancedMetricsService`.
- **Technical Acceptance Criteria:** Use case no longer calls `get_all_sales()`. It coordinates the port and the domain services correctly.

### Task 006 - [Adapter-Persistence]: Implement DuckDbSalesAdapter aggregations

- **Phase:** 3
- **Depends On:** Task 004
- **Parallel With:** —
- **Objective:** Write the actual SQL `GROUP BY`, `SUM`, `AVG` queries inside `DuckDbSalesAdapter` to implement the new port methods.
- **Files/Path:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py`
- **Reuse:** DuckDB connection setup.
- **Technical Acceptance Criteria:** All aggregations are performed natively via SQL in DuckDB.

### Task 007 - [Adapter-Persistence]: Deprecate get_all_sales

- **Phase:** 3
- **Depends On:** Task 006
- **Parallel With:** Task 008
- **Objective:** Remove `get_all_sales()` to eliminate OOM risks.
- **Files/Path:** `src/adapter/outbound/persistence/duckdb_sales_adapter.py`, `src/application/port/outbound/sales_data_port.py`
- **Reuse:** None.
- **Technical Acceptance Criteria:** The method is safely removed and no regressions are introduced.

### Task 008 - [Test-Integration]: End-to-end integration tests

- **Phase:** 3
- **Depends On:** Task 005, Task 006
- **Parallel With:** Task 007
- **Objective:** Verify that the DuckDB SQL pushdown logic returns identical results as the previous Python memory logic.
- **Files/Path:** `tests/integration/test_sales_metrics_integration.py`
- **Reuse:** Existing tests.
- **Technical Acceptance Criteria:** Assertions pass for all metrics, proving backward compatibility and adherence to PRD requirements.
