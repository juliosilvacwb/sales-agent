# T015 — Zero-Copy Remote S3 Direct Querying for Big Data Scalability

## PRD Reference

- **PRD:** [R015-s3-dynamic-dataset-storage.md](../business-requirements/R015-s3-dynamic-dataset-storage.md)
- **PS:** [PS015-s3-dynamic-dataset-storage.md](../product-strategy/PS015-s3-dynamic-dataset-storage.md)
- **Test Coverage:** [TEST015-s3-dynamic-dataset-storage.md](../tests/TEST015-s3-dynamic-dataset-storage.md)
- **Security Audit:** [S015-s3-dynamic-dataset-storage.md](../security/S015-s3-dynamic-dataset-storage.md)

## Technical Goal

Evolve `DuckDbSalesAdapter` to support **direct remote S3 querying** via DuckDB's `httpfs` extension, enabling zero-copy analytical execution against `s3://` URIs without loading the full dataset into container memory. The implementation must maintain 100% backward compatibility with local CSV paths, enforce cloud-native credential management via environment variables and Kubernetes Secrets, and guarantee bounded memory consumption (sub-512MB) regardless of dataset volume. All changes are strictly confined to the persistence adapter layer, preserving hexagonal architecture integrity.

## Architecture Decisions (ADRs)

### ADR-01: S3 Protocol Detection via URI Scheme

- **Decision:** Detect S3 datasets by checking if `dataset_path` starts with `s3://`. When detected, activate S3 mode; otherwise fall back to the existing local file path logic.
- **Trade-off Evaluated:** Evaluated explicit `STORAGE_TYPE` env var vs URI scheme autodetection. Chose URI scheme because it requires zero additional configuration, is self-documenting, and aligns with PRD01's requirement for seamless local/S3 switching via `DATASET_PATH`.
- **Ref:** PRD01, BR02.

### ADR-02: DuckDB httpfs Extension for S3 Streaming

- **Decision:** Use DuckDB's native `httpfs` extension (`INSTALL httpfs; LOAD httpfs;`) for streaming byte-range queries against S3. DuckDB natively supports S3 credential configuration via `SET s3_region`, `SET s3_access_key_id`, `SET s3_secret_access_key`, etc.
- **Trade-off Evaluated:** Evaluated `boto3` pre-download + local load vs DuckDB `httpfs` native streaming. Chose `httpfs` because it achieves true zero-copy (no local disk staging), leverages DuckDB's pushdown predicate optimization over HTTP range requests, and requires zero additional Python dependencies.
- **Dependency Impact:** **No new Python dependency required.** `httpfs` is a native DuckDB extension auto-installed at runtime. The existing `duckdb>=1.0.0` in `requirements.txt` already supports `httpfs`.
- **Ref:** PRD02, PRD04.

### ADR-03: VIEW Instead of TABLE for S3 Sources

- **Decision:** Create a `VIEW sales_data AS SELECT ... FROM read_csv_auto('s3://...')` instead of a `TABLE` when using S3. This ensures every query execution fetches the latest remote state (instant data freshness) without materialization.
- **Trade-off Evaluated:** Evaluated `CREATE TABLE AS` (snapshot) vs `CREATE VIEW` (live). Chose VIEW because PRD05 mandates instant data freshness and BR01 prohibits caching the full dataset locally.
- **Ref:** PRD04, PRD05, BR01.

### ADR-04: Conditional External Access Control

- **Decision:** When operating in S3 mode, DuckDB `enable_external_access` must remain `true` (since `httpfs` requires it). When operating in local mode, external access continues to be disabled (`SET enable_external_access = false;`) as the existing security hardening. AST query validation (R005 `SecuredSQLQueryTool`) continues to enforce read-only analytical boundaries regardless of mode.
- **Trade-off Evaluated:** Considered always disabling external access and using a separate DuckDB session. Chose conditional toggle because `httpfs` inherently requires external access, and R005 AST guardrails already block arbitrary file reads and mutations at the SQL layer.
- **Ref:** BR03, PRD07.

### ADR-05: AWS Credential Resolution from Environment Variables

- **Decision:** Read AWS credentials exclusively from environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_SESSION_TOKEN`, `AWS_ENDPOINT_URL`, `S3_USE_SSL`). Inject into DuckDB via `SET` statements before schema initialization. In Kubernetes, these are injected via Secrets.
- **Trade-off Evaluated:** Evaluated AWS credential chain (IRSA, instance profiles) vs explicit env vars. Chose env vars for maximum portability (local dev, CI, K8s) and alignment with the existing 12-factor pattern already established in the project.
- **Ref:** PRD03, BR02.

### ADR-06: Graceful Degradation on S3 Failures

- **Decision:** Wrap S3 view creation and credential configuration in try/except blocks. On failure (403 Forbidden, 404 Not Found, network timeout), log a clear diagnostic message and create an empty `sales_data` table with the canonical schema, allowing the agent to inform the user that no data is available rather than crashing.
- **Ref:** BR05, PRD08, Exception Path 1, Exception Path 2.

## Security & Reliability

### Security Mitigations

| Risk | Mitigation | Ref |
| --- | --- | --- |
| **Credential Leakage (CWE-798)** | AWS credentials are read from env vars (never hardcoded). DuckDB `SET` commands use parameterized values. Credentials are never logged. | PRD03, NFR Cloud-Native Security |
| **Arbitrary File Access via S3** | R005 AST validation continues to block `read_csv`, `read_text`, `glob`, `COPY`, `ATTACH` functions even when external access is enabled for `httpfs`. | BR03, ADR-04 |
| **PII Exposure in Error Messages** | S3 URIs in error messages are sanitized using the existing `_sanitize_path_details` pattern (`[REDACTED_PATH]`). | BR05 |

### Reliability Mitigations

| Risk | Mitigation | Ref |
| --- | --- | --- |
| **OOM on Large Datasets** | VIEW-based streaming queries with pushdown predicates. No `CREATE TABLE AS` materialization for S3. | BR01, AC03 |
| **S3 Network Timeout** | Graceful try/except with actionable logging. Empty schema fallback. | BR05, Exception Path 1/2 |
| **Stale Data** | VIEW ensures every query hits live S3 state. Zero cache. | PRD05, AC04 |

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Domain Core (Zero framework dependencies)

#### Leaf nodes (fully parallel — no domain dependencies)

- [COMPLETED] Task 001 - [Domain-Exception]: Create `S3ConnectionError` domain exception (Depends On: —)

### 🟡 Phase 2 — Ports & Use Cases (All tasks parallel-safe | Depends on Phase 1)

> **Note:** The existing `SalesDataPort` interface and `SalesMetricsApplicationService` require **zero modifications**. The S3 integration is entirely encapsulated within the persistence adapter (Phase 3), which already implements the `SalesDataPort` contract. The `profile_dataset()` method on the port is also unchanged.

- [COMPLETED] Task 002 - [Port-Out]: No changes required to `SalesDataPort` — verified interface compatibility (Depends On: Task 001)

### 🟢 Phase 3 — Adapters (All tasks parallel-safe | Depends on Phase 2)

- [COMPLETED] Task 003 - [Adapter-Persistence]: Implement S3 URI detection and `httpfs` extension management in `DuckDbSalesAdapter._initialize_schema()` (Depends On: Task 002)
- [COMPLETED] Task 004 - [Adapter-Persistence]: Implement AWS credential configuration via DuckDB `SET` commands in `DuckDbSalesAdapter` (Depends On: Task 002)
- [COMPLETED] Task 005 - [Adapter-Persistence]: Implement S3 VIEW creation (`CREATE VIEW sales_data AS SELECT ... FROM read_csv_auto('s3://...')`) with graceful degradation (Depends On: Task 003, Task 004)
- [COMPLETED] Task 006 - [Adapter-Persistence]: Implement conditional `enable_external_access` toggle (enabled for S3, disabled for local) (Depends On: Task 005)
- [COMPLETED] Task 007 - [Config]: Update `.env.example` with S3 environment variables documentation (Depends On: —)
- [COMPLETED] Task 008 - [Config]: Update `k8s/configmap.yaml` with `DATASET_PATH` S3 URI example and `k8s/secrets.example.yaml` with AWS credential keys (Depends On: —)
- [COMPLETED] Task 009 - [Config]: Update `Dockerfile` to remove `COPY dataset/` and default `DATASET_PATH` to S3 URI support (Depends On: —)

### 🔴 Phase 4 — Testing & Integration Verification (Depends on Phase 3)

- [COMPLETED] Task 010 - [Test-Unit]: Unit tests for S3 URI detection logic (local vs `s3://` paths) (Depends On: Task 003)
- [COMPLETED] Task 011 - [Test-Unit]: Unit tests for `httpfs` extension installation and AWS credential `SET` commands with mocked DuckDB connection (Depends On: Task 004)
- [COMPLETED] Task 012 - [Test-Unit]: Unit tests for graceful degradation on S3 403/404 errors (Depends On: Task 005)
- [COMPLETED] Task 013 - [Test-Unit]: Unit test verifying `enable_external_access` is `true` for S3 and `false` for local (Depends On: Task 006)
- [COMPLETED] Task 014 - [Test-Unit]: Regression tests confirming backward compatibility with local CSV paths (Depends On: Task 005)
- [COMPLETED] Task 015 - [Test-Integration]: End-to-end test executing domain aggregations against mocked/LocalStack S3 dataset (Depends On: Task 005)
- [COMPLETED] Task 016 - [Test-Integration]: Test `profile_dataset()` execution against S3 URI (Depends On: Task 005)

## Task Detailing (Summary Tasks)

### Task 001 - [Domain-Exception]: Create `S3ConnectionError` domain exception

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** — (leaf node)
- **Objective:** Create a domain exception for S3-specific connection errors (auth failures, missing objects, network timeouts) to provide clear error semantics without coupling to DuckDB or AWS SDK types.
- **Files/Path:** `src/domain/exception/s3_exceptions.py`
- **Reuse:** Follow the existing pattern in [auth_exceptions.py](file:///c:/Code/challenge_ai_engineer/src/domain/exception/auth_exceptions.py) — pure Python exceptions with zero framework imports.
- **Technical Acceptance Criteria:**
  - Pure Python class extending `Exception`.
  - Includes `message: str` and optional `status_code: int` (e.g., 403, 404) attributes.
  - Zero framework imports.
  - Unit test validates exception instantiation and attribute access.

### Task 002 - [Port-Out]: Verify SalesDataPort interface compatibility

- **Phase:** 2
- **Depends On:** Task 001
- **Parallel With:** —
- **Objective:** Confirm that the existing [SalesDataPort](file:///c:/Code/challenge_ai_engineer/src/application/port/outbound/sales_data_port.py) interface requires zero modifications for S3 support. The `profile_dataset()`, all aggregation methods, and `execute_read_only_query()` operate on the abstract `sales_data` view/table regardless of storage backend.
- **Files/Path:** `src/application/port/outbound/sales_data_port.py` (READ-ONLY verification, no changes expected)
- **Technical Acceptance Criteria:**
  - Port interface remains unchanged.
  - All method signatures continue to use domain types only.
  - Document verification result in task completion notes.

### Task 003 - [Adapter-Persistence]: Implement S3 URI detection and httpfs extension management

- **Phase:** 3
- **Depends On:** Task 002
- **Parallel With:** Task 007, Task 008, Task 009
- **Objective:** Modify `DuckDbSalesAdapter.__init__()` and `_initialize_schema()` to detect `s3://` URIs and dynamically install/load the DuckDB `httpfs` extension.
- **Files/Path:** [duckdb_sales_adapter.py](file:///c:/Code/challenge_ai_engineer/src/adapter/outbound/persistence/duckdb_sales_adapter.py)
- **Reuse:** Existing `_initialize_schema()` method.
- **Technical Acceptance Criteria:**
  - Add `self._is_s3` boolean property based on `self._dataset_path.lower().startswith("s3://")`.
  - When `_is_s3` is `True`, execute `INSTALL httpfs; LOAD httpfs;` before schema initialization.
  - When `_is_s3` is `False`, existing local CSV loading path is preserved unchanged.
  - Log clear messages: `[S3_MODE] Detected S3 URI, installing httpfs extension...`

### Task 004 - [Adapter-Persistence]: Implement AWS credential configuration

- **Phase:** 3
- **Depends On:** Task 002
- **Parallel With:** Task 003, Task 007, Task 008, Task 009
- **Objective:** Implement a private method `_configure_s3_credentials()` that reads AWS environment variables and injects them into the DuckDB session via `SET` commands.
- **Files/Path:** [duckdb_sales_adapter.py](file:///c:/Code/challenge_ai_engineer/src/adapter/outbound/persistence/duckdb_sales_adapter.py)
- **Technical Acceptance Criteria:**
  - Read from env vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (fallback `AWS_DEFAULT_REGION`), `AWS_SESSION_TOKEN` (optional), `AWS_ENDPOINT_URL` / `S3_ENDPOINT` (optional), `S3_USE_SSL` (optional, default `true`).
  - Execute DuckDB `SET` commands: `SET s3_region = '...'`, `SET s3_access_key_id = '...'`, etc.
  - Credentials are **never logged** (use `logger.info("[S3_MODE] AWS credentials configured successfully")` without values).
  - Missing mandatory credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) raise `S3ConnectionError`.

### Task 005 - [Adapter-Persistence]: Implement S3 VIEW creation with graceful degradation

- **Phase:** 3
- **Depends On:** Task 003, Task 004
- **Parallel With:** Task 007, Task 008, Task 009
- **Objective:** When in S3 mode, create a `VIEW sales_data` pointing to the remote CSV via `read_csv_auto('s3://...', delim=';', header=true)` with the same column casting as the current local TABLE creation. Wrap in try/except for graceful degradation.
- **Files/Path:** [duckdb_sales_adapter.py](file:///c:/Code/challenge_ai_engineer/src/adapter/outbound/persistence/duckdb_sales_adapter.py)
- **Reuse:** Reuse the existing column CAST expressions from the local path `CREATE TABLE` query.
- **Technical Acceptance Criteria:**
  - S3 path creates `CREATE VIEW IF NOT EXISTS sales_data AS SELECT [casted_columns] FROM read_csv_auto('s3://...', delim=';', header=true)`.
  - On DuckDB error (HTTP 403, 404, network timeout), catch exception, log actionable diagnostic (`[S3_MODE] Failed to create S3 view: ...`), and fall back to empty table with canonical schema (BR05).
  - VIEW exposes identical columns as the local TABLE: `product_id`, `local`, `date`, `planned_quantity`, `actual_quantity`, `planned_price`, `actual_price`, `service_level`, `promotion_type` (BR04).

### Task 006 - [Adapter-Persistence]: Implement conditional external access toggle

- **Phase:** 3
- **Depends On:** Task 005
- **Parallel With:** Task 007, Task 008, Task 009
- **Objective:** After schema initialization, set `enable_external_access = false` only when in local mode. In S3 mode, leave external access enabled (required by `httpfs` for ongoing queries).
- **Files/Path:** [duckdb_sales_adapter.py](file:///c:/Code/challenge_ai_engineer/src/adapter/outbound/persistence/duckdb_sales_adapter.py)
- **Technical Acceptance Criteria:**
  - Local mode: `SET enable_external_access = false` (existing behavior preserved).
  - S3 mode: External access remains enabled. Log: `[S3_MODE] External access remains enabled for S3 streaming queries`.
  - AST guardrails (R005) continue to operate independently.

### Task 007 - [Config]: Update `.env.example` with S3 environment variables

- **Phase:** 3
- **Depends On:** —
- **Parallel With:** Task 003, Task 004, Task 005, Task 006, Task 008, Task 009
- **Objective:** Add documented S3 environment variables to the `.env.example` file.
- **Files/Path:** [.env.example](file:///c:/Code/challenge_ai_engineer/.env.example)
- **Technical Acceptance Criteria:**
  - Add section `# S3 Remote Dataset Configuration (Zero-Copy Querying)` with variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_SESSION_TOKEN`, `AWS_ENDPOINT_URL`, `S3_USE_SSL`.
  - Add comment showing example: `# DATASET_PATH=s3://juliosilvacwb-private/sales.csv`.
  - Existing variables remain unchanged.

### Task 008 - [Config]: Update K8s manifests for S3 credentials

- **Phase:** 3
- **Depends On:** —
- **Parallel With:** Task 003, Task 004, Task 005, Task 006, Task 007, Task 009
- **Objective:** Update `k8s/configmap.yaml` to show S3 URI as `DATASET_PATH` option and update `k8s/secrets.example.yaml` with AWS credential keys. Update `k8s/app-deployment.yaml` to inject AWS credentials from secrets.
- **Files/Path:** [configmap.yaml](file:///c:/Code/challenge_ai_engineer/k8s/configmap.yaml), [secrets.example.yaml](file:///c:/Code/challenge_ai_engineer/k8s/secrets.example.yaml), [app-deployment.yaml](file:///c:/Code/challenge_ai_engineer/k8s/app-deployment.yaml)
- **Technical Acceptance Criteria:**
  - `configmap.yaml`: Change `DATASET_PATH` to `s3://juliosilvacwb-private/sales.csv` and add `AWS_REGION: "us-east-1"`.
  - `secrets.example.yaml`: Add `aws-access-key-id`, `aws-secret-access-key`, and optional `aws-session-token` keys.
  - `app-deployment.yaml`: Add env entries reading AWS credentials from `sales-agent-secrets`.

### Task 009 - [Config]: Update Dockerfile for S3-first deployment

- **Phase:** 3
- **Depends On:** —
- **Parallel With:** Task 003, Task 004, Task 005, Task 006, Task 007, Task 008
- **Objective:** Update the Dockerfile to remove the mandatory `COPY dataset/` directive (dataset is now remote in S3) and set the default `DATASET_PATH` to support S3 URIs. Keep the `COPY dataset/` as optional for backward compatibility.
- **Files/Path:** [Dockerfile](file:///c:/Code/challenge_ai_engineer/Dockerfile)
- **Technical Acceptance Criteria:**
  - Change `DATASET_PATH` default from `/app/dataset/sales.csv` to empty or document S3 override.
  - Add comment explaining S3 vs local mode.
  - Container must still work with local CSV if `DATASET_PATH` points to a local file.

### Task 010 - [Test-Unit]: S3 URI detection logic tests

- **Phase:** 4
- **Depends On:** Task 003
- **Parallel With:** Task 011, Task 012, Task 013, Task 014
- **Objective:** Verify that the adapter correctly identifies `s3://` URIs vs local paths.
- **Files/Path:** `tests/unit/test_s3_uri_detection.py`
- **Technical Acceptance Criteria:**
  - Test `s3://bucket/file.csv` → `_is_s3 = True`.
  - Test `/app/dataset/sales.csv` → `_is_s3 = False`.
  - Test `dataset/sales.csv` (relative) → `_is_s3 = False`.
  - Test `S3://Bucket/File.csv` (uppercase) → `_is_s3 = True`.

### Task 011 - [Test-Unit]: httpfs and credential configuration tests

- **Phase:** 4
- **Depends On:** Task 004
- **Parallel With:** Task 010, Task 012, Task 013, Task 014
- **Objective:** Verify `httpfs` installation and AWS credential `SET` commands are emitted correctly.
- **Files/Path:** `tests/unit/test_s3_credential_config.py`
- **Technical Acceptance Criteria:**
  - Mock `duckdb.connect()` and verify `INSTALL httpfs`, `LOAD httpfs` are called.
  - Verify `SET s3_region`, `SET s3_access_key_id`, `SET s3_secret_access_key` are called with values from env vars.
  - Verify optional parameters (`s3_session_token`, `s3_endpoint`, `s3_use_ssl`) are only set when present.
  - Verify `S3ConnectionError` is raised when mandatory credentials are missing.

### Task 012 - [Test-Unit]: Graceful degradation on S3 errors

- **Phase:** 4
- **Depends On:** Task 005
- **Parallel With:** Task 010, Task 011, Task 013, Task 014
- **Objective:** Verify that S3 403/404 errors during VIEW creation result in graceful fallback.
- **Files/Path:** `tests/unit/test_s3_graceful_degradation.py`
- **Technical Acceptance Criteria:**
  - Simulate DuckDB exception on VIEW creation.
  - Assert empty `sales_data` table is created with canonical schema.
  - Assert warning log is emitted with actionable message.
  - Assert adapter remains functional (does not crash).

### Task 013 - [Test-Unit]: Conditional external access toggle

- **Phase:** 4
- **Depends On:** Task 006
- **Parallel With:** Task 010, Task 011, Task 012, Task 014
- **Objective:** Verify `enable_external_access` behavior per mode.
- **Files/Path:** `tests/unit/test_s3_external_access.py`
- **Technical Acceptance Criteria:**
  - In local mode: `SET enable_external_access = false` is executed.
  - In S3 mode: `SET enable_external_access = false` is **NOT** executed.

### Task 014 - [Test-Unit]: Backward compatibility regression tests

- **Phase:** 4
- **Depends On:** Task 005
- **Parallel With:** Task 010, Task 011, Task 012, Task 013
- **Objective:** Verify existing local CSV functionality is unbroken.
- **Files/Path:** `tests/unit/test_s3_backward_compatibility.py`
- **Reuse:** Existing test fixtures in `tests/fixtures/`.
- **Technical Acceptance Criteria:**
  - Initialize `DuckDbSalesAdapter` with local CSV path.
  - Execute all 10 aggregation methods and `execute_read_only_query`.
  - Assert results match existing baseline.
  - Assert `profile_dataset()` returns valid `DatasetProfile`.

### Task 015 - [Test-Integration]: End-to-end domain aggregations against S3

- **Phase:** 4
- **Depends On:** Task 005
- **Parallel With:** Task 016
- **Objective:** Validate that all 10 domain aggregations and `SecuredSQLQueryTool` execute correctly against an S3-backed `sales_data` view.
- **Files/Path:** `tests/integration/test_s3_aggregations.py`
- **Technical Acceptance Criteria:**
  - Use either a real S3 bucket (if credentials available) or LocalStack/MinIO mock.
  - Execute each aggregation method and verify non-null results.
  - Verify `execute_read_only_query("SELECT COUNT(*) FROM sales_data")` returns valid count.
  - Mark as `@pytest.mark.skipif` when no S3 credentials are available (CI/CD compatibility).

### Task 016 - [Test-Integration]: Dataset profiling against S3

- **Phase:** 4
- **Depends On:** Task 005
- **Parallel With:** Task 015
- **Objective:** Verify `profile_dataset()` computes valid metadata from S3 source.
- **Files/Path:** `tests/integration/test_s3_profiling.py`
- **Technical Acceptance Criteria:**
  - Execute `profile_dataset()` against S3 URI.
  - Assert `total_records > 0`, date bounds are valid, distinct counts are populated.
  - Assert `null_representations` and `constant_columns` are detected correctly.
  - Mark as `@pytest.mark.skipif` when no S3 credentials are available.

## Parallelism Metrics

| Metric | Value |
| --- | --- |
| Total Tasks | 16 |
| Phase 1 (Domain) | 1 task |
| Phase 2 (Ports) | 1 task (verification only) |
| Phase 3 (Adapters) | 7 tasks (max 7 parallel) |
| Phase 4 (Testing) | 7 tasks (max 7 parallel) |
| Parallelism Ratio | **87.5%** (14 of 16 tasks executable in parallel within phases) |
