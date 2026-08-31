# PRD: Zero-Copy Remote S3 Direct Querying for Big Data Scalability

## Summary

Origin: [PS015-s3-dynamic-dataset-storage.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS015-s3-dynamic-dataset-storage.md), Recommendation: Top Recommendation (Direct S3 Analytical Execution).

The **Sales Data Analysis Agent** is scaling toward enterprise-grade data volumes, where sales datasets can scale to hundreds of millions or billions of records. In this scale regime, loading entire datasets into container RAM (in-memory tables) causes memory exhaustion (OOM), requires expensive pod provisioning, and introduces data staleness windows whenever source data is updated in object storage.

To achieve infinite dataset scalability, minimal memory footprint, and instant data freshness, this PRD specifies the implementation of **Zero-Copy Remote S3 Direct Analytical Querying**. DuckDB will query remote datasets directly on AWS S3 (`s3://juliosilvacwb-private/sales.csv`) using streaming range requests and pushdown aggregates via DuckDB's native `httpfs` extension.

This architectural shift decouples compute from storage, allowing stateless application pods to run with minimal RAM (256MB-512MB) while querying multi-gigabyte or terabyte datasets with immediate visibility into external ETL updates.

## Functional Requirements

- **PRD01 (Remote S3 Dataset URI Configuration):** The system must support configuring remote S3 dataset URIs (e.g., `s3://juliosilvacwb-private/sales.csv`) via environment variables (`DATASET_PATH` or `DATASET_S3_URI`), seamlessly distinguishing between local paths and `s3://` URIs.
- **PRD02 (DuckDB S3 & httpfs Extension Management):** The persistence adapter must dynamically install, load, and configure DuckDB's `httpfs` extension to support HTTP/S3 remote streaming queries.
- **PRD03 (S3 Credential & Endpoint Configuration):** The persistence adapter must support AWS authentication via standard environment variables:
  - `AWS_ACCESS_KEY_ID`: Access key identifier.
  - `AWS_SECRET_ACCESS_KEY`: Secret access key.
  - `AWS_REGION` / `AWS_DEFAULT_REGION`: AWS region (e.g., `us-east-1`).
  - `AWS_SESSION_TOKEN`: Optional session token for temporary STS credentials.
  - `AWS_ENDPOINT_URL` / `S3_ENDPOINT`: Optional custom endpoint for MinIO / LocalStack testing.
  - `S3_USE_SSL`: Optional toggle (default `true`) for SSL verification.
- **PRD04 (Zero-Copy View / Direct Query Execution):** The system must create a virtual `sales_data` view directly pointing to the S3 source (`read_csv_auto('s3://...')` with delimiter `;`), executing queries on demand with byte-range pushdown without preloading the entire dataset into memory.
- **PRD05 (Instant Data Freshness):** Because queries execute against the remote S3 view directly, updates, appends, or overwrites made to the S3 dataset must be reflected on subsequent queries without requiring application restarts or manual cache invalidations.
- **PRD06 (Dynamic Data Profiler Compatibility):** The dynamic dataset profiler (R011) must compute schema metadata, summary statistics, and sample values directly against the remote S3 dataset using lightweight aggregate queries.
- **PRD07 (Domain Aggregations & SQL Tool Support):** All 10 domain analytical aggregations (Total Sales, Top Products, Price Elasticity, etc.) and `SecuredSQLQueryTool` (R005) must execute seamlessly against the remote S3 view.
- **PRD08 (Backward Compatibility & Offline Fallback):** The system must maintain 100% backward compatibility with local CSV files (e.g., `/app/dataset/sales.csv` or relative file paths), enabling offline unit testing and development without cloud dependencies.

## Non-Functional Requirements

- **Architectural Decoupling (Hexagonal Architecture):** All S3 connection management, extension loading, and remote view creation must be encapsulated strictly within `DuckDbSalesAdapter` (`src/adapter/outbound/persistence/duckdb_sales_adapter.py`). Domain models, use cases, and LLM inbound adapters remain agnostic to storage topology.
- **Memory Footprint & Predictability:** Pod memory consumption must remain flat and bounded (sub-512MB RAM) regardless of dataset volume, preventing Out-Of-Memory (OOM) kills.
- **Cloud-Native Security:** AWS credentials must never be hardcoded or logged in plaintext. They must be injected via Kubernetes Secrets and environment variables.
- **Resilience & Fault Tolerance:** Network timeouts, missing S3 objects, or authentication errors must be caught gracefully and logged with actionable technical messages without crashing the service.
- **Testability:** The implementation must support mocked S3 tests, LocalStack/MinIO fixtures, and offline fallback mode for standard CI/CD execution.

## Business Rules

- **BR01 (Storage-Compute Decoupling):** Application pods must not cache or store full copies of the remote S3 dataset in local disk or RAM.
- **BR02 (Credential Resolution Order):** When an `s3://` URI is detected, DuckDB S3 configuration parameters (`s3_region`, `s3_access_key_id`, `s3_secret_access_key`, `s3_session_token`, `s3_endpoint`, `s3_use_ssl`) must be injected into the active DuckDB connection before schema initialization.
- **BR03 (Controlled External Access):** When S3 querying is enabled, DuckDB external access must be permitted for S3 HTTP/HTTPS endpoints, while AST query validation (R005) continues to restrict arbitrary execution and enforce read-only analytical boundaries.
- **BR04 (Schema Uniformity):** The `sales_data` view must expose identical column names and types (`product_id`, `local`, `date`, `planned_quantity`, `actual_quantity`, `planned_price`, `actual_price`, `service_level`, `promotion_type`) regardless of whether the source is local or S3.
- **BR05 (Graceful Degradation):** If S3 access fails during startup or query time, the system must log diagnostic details (e.g., HTTP 403 Forbidden or 404 Not Found) and raise clear domain exceptions instead of crashing the process.

## Critical Data (Conceptual)

- **Storage Target Metadata:**
  - `storage_type`: `"local"` or `"s3"`.
  - `dataset_uri`: S3 bucket URI (`s3://...`) or filesystem path (`/app/dataset/...`).
  - `s3_region`: AWS region.
  - `s3_endpoint`: Custom S3 endpoint URL (optional).
- **Execution Telemetry:**
  - Remote scan duration (ms).
  - Query execution latency.
  - Result row count.
- **Dataset Profile Metadata (R011):**
  - Row count estimate.
  - Date ranges (min/max date).
  - Unique product/location counts.

## User Flow

### Happy Path 1 (Direct Querying against Remote S3 Dataset)

1. The Kubernetes deployment starts with `DATASET_PATH="s3://juliosilvacwb-private/sales.csv"` and AWS credentials injected via secrets.
2. `DuckDbSalesAdapter` initializes, installs/loads `httpfs`, configures AWS credentials in the DuckDB session, and creates the `sales_data` view on the S3 URI.
3. A user asks: "Qual é o faturamento total em 2024?".
4. `SalesAgent` triggers `get_total_sales_in_period(start_date="2024-01-01", end_date="2024-12-31")`.
5. DuckDB streams only relevant byte ranges from S3, applies the date filter, aggregates totals, and returns the result in milliseconds.
6. The agent synthesizes the response with zero dataset loaded into local RAM.

### Happy Path 2 (Instant Data Freshness upon S3 Dataset Overwrite)

1. External ETL pipeline appends new transactions to `s3://juliosilvacwb-private/sales.csv`.
2. A user immediately asks: "Qual o total de vendas de hoje?".
3. DuckDB queries the remote S3 object directly, immediately reading the latest data.
4. No pod restart or cache invalidation is required.

### Exception Path 1 (Invalid S3 Credentials or Unauthorized Access)

1. Application initializes with expired or invalid `AWS_SECRET_ACCESS_KEY`.
2. S3 view creation or query execution raises an S3 403 Forbidden error.
3. `DuckDbSalesAdapter` logs a clear error ("AWS S3 authentication failed: verify AWS credentials").
4. The system reports a graceful service error without unhandled kernel crashes.

### Exception Path 2 (S3 Object Not Found)

1. Application is configured with a non-existent S3 URI (`s3://invalid-bucket/nonexistent.csv`).
2. DuckDB raises a 404 Not Found error.
3. `DuckDbSalesAdapter` logs a warning and creates an empty fallback schema, allowing the agent to inform the user that no sales data is available.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | `DuckDbSalesAdapter` accepts `s3://` URIs and configures DuckDB `httpfs` and AWS session parameters. | Unit test verifying S3 session initialization with mocked credentials and URI. |
| AC02 | Analytical aggregations execute successfully against an S3 dataset URI via streaming range requests. | Integration test running domain aggregations against remote/mocked S3 dataset. |
| AC03 | Memory footprint remains constant and under 512MB during large dataset query execution. | Resource profiling / memory benchmark test during query execution. |
| AC04 | Modifying or appending data in S3 is immediately visible on the next query without pod restart. | Integration test verifying instant data freshness after S3 object update. |
| AC05 | Local dataset paths (`/path/to/sales.csv`) continue to work seamlessly without S3 dependencies. | Regression test suite execution on local CSV fixtures. |
| AC06 | Dynamic dataset profiling (R011) generates valid metadata and statistics from S3 source. | Unit test executing `get_dataset_profile` against an S3 URI. |
| AC07 | Secured SQL AST validation (R005) operates normally over S3-backed `sales_data` view. | Test executing `SecuredSQLQueryTool` against S3 view with valid and invalid SQL statements. |
| AC08 | S3 connection or permission errors produce clear, actionable logs and graceful domain errors. | Negative test asserting proper error handling on simulated S3 403/404 responses. |
