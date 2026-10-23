# T016 — Database Query MCP Server Core (Oracle DB, SQL Server, PostgreSQL and MySQL)

## PRD Reference

- **PRD:** [R016-database-query-mcp-tool.md](../business-requirements/R016-database-query-mcp-tool.md)
- **Product Strategy:** [PS016-database-query-mcp-tool.md](../product-strategy/PS016-database-query-mcp-tool.md)
- **Delivery Location:** the implementation occurs in a **new, independent repository** (controlled extraction from the `sales-agent`). All `Files/Path` references below are relative to the new repository root `database-query-mcp-server/`. The `sales-agent` source remains untouched (PS001–PS015 immutable).

## Technical Goal

Design and specify a **standalone MCP (Model Context Protocol) server** that extracts the proven SQL-read-only capability of the Sales Agent (`SqlSecurityValidator`, `ParsedSqlStatement`, `SqlSyntaxError`, sanitization patterns and error contract) and generalizes it to **four relational databases**: Oracle DB, SQL Server, PostgreSQL and MySQL.

The server exposes the tools `execute_query`, `list_databases`, `list_tables` and `get_table_schema`, delivers the **database catalog at session initialization**, applies **sensitive data sanitization** (passwords, tokens, API keys) on every response, preserves the **self-correctable error contract**, and remains **100% deterministic and LLM-free**. The architecture follows the hexagonal-parallelism skill: a pure Domain core (zero framework dependencies), Application Ports and Use Cases, and a parallel-safe Adapter layer (transport, per-dialect parsers, per-database connections, serialization).

## Architecture Decisions (ADRs)

### ADR-01: Controlled Copy (Extraction) Instead of Dependency

- **Decision:** The new repository receives a **controlled copy** of the relevant pure-domain pieces from `sales-agent/src/domain/` (`sql_security_validator.py`, `sql_validation.py`, `sql_validation_exceptions.py`), generalized for four dialects. Zero runtime or import dependency on any `sales-agent` module is permitted.
- **Trade-off Evaluated:** Evaluated vendoring via git submodule/package dependency vs controlled copy. Chose controlled copy because PS016/R016 mandate an independent self-contained repository with its own semantic versioning and CI/CD, and PRD03/AC01 explicitly require zero imports from the source monolith.
- **Ref:** PRD03, AC01.

### ADR-02: FastMCP (Official Python SDK) as MCP Transport

- **Decision:** Use the official MCP Python SDK (`mcp[cli]` / FastMCP) to implement the server, tools and session initialization discovery. The MCP transport is an inbound adapter that delegates all logic to the Application layer.
- **Trade-off Evaluated:** Evaluated raw HTTP/JSON-RPC implementation vs official SDK. Chose FastMCP because it is the reference implementation of the MCP spec, provides native tool discovery (catalog at initialization), stdio/HTTP transport, and keeps the transport decoupled from business logic.
- **Dependency Impact:** **One new justified dependency** (`mcp`). Required to speak the MCP wire protocol; cannot be replaced by existing project libraries.
- **Ref:** PRD01, PRD02, PRD05.

### ADR-03: sqlglot as the Multi-Dialect AST Engine

- **Decision:** Reuse `sqlglot` as the single parsing engine, parameterized per registered database type: `dialect="oracle"`, `dialect="tsql"` (SQL Server), `dialect="postgres"`, `dialect="mysql"`. The parser adapter maps raw SQL to the domain `ParsedSqlStatement` regardless of dialect.
- **Trade-off Evaluated:** Evaluated per-database official parsers vs a single multi-dialect parser. Chose `sqlglot` because it is already battle-tested in the Sales Agent (R005), supports the four required dialects, and keeps the structural validation rules dialect-agnostic (PRD08). The validation rules (root `SELECT`/`WITH`/`UNION`, forbidden mutational nodes, stacked query rejection) remain identical in intent across dialects.
- **Dependency Impact:** Reuses the existing `sqlglot>=26.0.0` dependency (no new library).
- **Ref:** PRD08, AC04, AC05.

### ADR-04: Deterministic Sanitization as Pure Domain Service

- **Decision:** The sensitive-data sanitization (passwords, tokens, API keys) is a **pure Domain Service** (`SensitiveDataSanitizer`) operating on domain models, with two complementary strategies: (1) **by schema** — per-database sensitive column policy (allowlist/denylist); (2) **by value heuristics** — regex patterns for `Authorization:`, `Bearer`, JWT, prefixed keys (`AKIA`, `sk-`), connection strings and session tokens. Values are replaced with `[REDACTED]` and the response signals redaction explicitly.
- **Trade-off Evaluated:** Evaluated sanitization inside the JSON serializer adapter vs domain service invoked by the use case. Chose domain service because redaction decisions are business-critical (fail-closed default per BR05/NFR) and must be unit-testable independently of transport/serialization and shared between response and log pipelines (PRD14).
- **Ref:** PRD12, PRD13, PRD14, BR05, CWE-200/209/532.

### ADR-05: Duplicated Read-Only Defense (AST + Native Connection)

- **Decision:** Read-only enforcement is layered: (1) first line of defense — deterministic AST validation (PRD08); (2) second line — each connection adapter establishes the database session in its **native read-only mode** (e.g., `SET TRANSACTION READ ONLY` / read-only user / `default_transaction_read_only`), so a guardrail bypass cannot mutate data (PRD18). The startup validator (Task 032) verifies this posture per connection.
- **Trade-off Evaluated:** Evaluated relying only on AST blocking vs layering native read-only. Chose layering because AST validates syntax, not database privileges (PS016 Ideas 6/17); defense in depth is the standing project posture.
- **Ref:** PRD09, PRD18, BR01.

### ADR-06: Connection Registry via Environment Variables with Reserved Version Field

- **Decision:** Connections are registered via env blocks `DB_<ALIAS>_*` parsed by `EnvConnectionRegistry`: mandatory `TYPE` and reserved `VERSION` (e.g., `oracle_19c`) for the future version compatibility matrix (PS016 Idea 17, Package 3). The registry validates all connections at startup and fails fast with a credential-free diagnostic (PRD10).
- **Trade-off Evaluated:** Evaluated JSON/YAML config file vs env vars. Chose env vars (12-factor, NFR Configurability) aligned with the project's existing pattern (`DATASET_PATH`, `.env.example`).
- **Ref:** PRD04, PRD10, AC13, BR08.

### ADR-07: Structured Error Contract Preserved and Generalized

- **Decision:** Every failure mode returns a categorized, sanitized error with explicit correction guidance: `SQL_SYNTAX_ERROR`, `DISALLOWED_ROOT_OPERATION`, `FORBIDDEN_MUTATIONAL_NODE`, `FORBIDDEN_FUNCTION_CALL`, `STACKED_QUERIES_DETECTED`, `EMPTY_RESULT_SET`, plus connection/execution categories. Stack traces, paths (`[REDACTED_PATH]`) and credentials are never exposed (PRD11, BR04).
- **Trade-off Evaluated:** Evaluated raw DB exception propagation vs categorized contract. Chose the categorized contract because PRD11/BR04 mandate self-correction guidance and the consuming agent is the one that self-corrects (BR07).
- **Ref:** PRD11, AC07, AC08.

### ADR-08: Schema Discovery via Native Metadata Catalogs

- **Decision:** `list_tables(database)` and `get_table_schema(database, table)` read the native metadata catalog of the target database (e.g., `information_schema` for PostgreSQL/MySQL, `sys.tables`/`INFORMATION_SCHEMA` for SQL Server, `ALL_TABLES`/`ALL_TAB_COLUMNS` for Oracle). Sensitive columns are flagged in schema metadata without exposing values (PRD17).
- **Trade-off Evaluated:** Evaluated a unified generic metadata query vs native catalogs per type. Chose native catalogs because each database exposes different naming/privilege semantics (PS016 Idea 13).
- **Ref:** PRD17, AC14.

### ADR-09: Response Serialization with Truncation, Redaction and Safe JSON

- **Decision:** `JsonResponseSerializer` serializes results as structured JSON preserving column structure and counting, with `ensure_ascii=False`, safe string conversion for non-JSON-native types (`default=str`), per-database row ceiling (inherited default 50) with truncation notice (total vs returned), and applies the domain sanitizer before serialization.
- **Trade-off Evaluated:** n/a — behavioral inheritance from the Sales Agent `MAX_RESULTS = 50` pattern (R005) to satisfy PRD15/PRD16/AC12.
- **Ref:** PRD15, PRD16, AC12.

### ADR-10: Structured Observability with Mandatory Redaction

- **Decision:** A `StructuredLoggingAdapter` emits one structured record per invocation (agent/key, database, query, duration, status, returned rows, redaction flags). Credentials, paths and sensitive values are redacted before logging by the same sanitizer used for responses (PRD14).
- **Trade-off Evaluated:** Evaluated logging raw query text vs sanitized query. Chose sanitized query text to preserve debuggability while honoring BR05/AC11 (no credentials or sensitive data in logs).
- **Ref:** PRD14, AC11.

## Security & Reliability

### Security Mitigations

| Risk | Mitigation | Ref |
| --- | --- | --- |
| **Sensitive Data Leakage (CWE-200)** | `SensitiveDataSanitizer` (schema policy + value heuristics) replaces passwords/tokens/API keys with `[REDACTED]` in responses; redaction flagged per response. | PRD12, PRD13, AC09, AC10 |
| **Credential Exposure in Errors/Logs (CWE-209, CWE-532)** | Connection/query errors sanitized (`[REDACTED_PATH]`, credentials stripped) by the same sanitizer before logging; structured logs never contain secrets. | PRD14, BR04, AC11 |
| **SQL Injection / Mutational SQL (CWE-89)** | Deterministic AST guardrail blocks DDL/DML at any depth plus stacked queries, per dialect. Same rules as R005, extended to 4 dialects. | PRD08, AC04, AC06 |
| **Mutation via Guardrail Bypass** | Native read-only session per database (layer 2) plus AST (layer 1); startup validation verifies read-only posture. | PRD09, PRD18, AC13 |
| **Connection String Secrets in Startup Diagnostics** | Fail-fast diagnostics are credential-free; registry redacts values before surfacing configuration issues. | PRD10, BR08, AC13 |
| **Resource Exhaustion (full scan)** | Per-database row ceiling (default 50) and timeout; truncation notice informs agent. | PRD15, AC12 |
| **Prompt Injection Driving Harmful SQL** | Server is LLM-free and deterministic; validation is structural, not semantic. | PRD02, AC15 |

### Reliability Mitigations

| Risk | Mitigation | Ref |
| --- | --- | --- |
| **Invalid/Unreachable Connection at Startup** | `EnvConnectionRegistry` validates every connection at startup and fails fast with diagnostic. | PRD10, AC13 |
| **Connection Drop Mid-Session** | Per-call categorized connection error with guidance; agent retries or selects another catalog entry. | PRD11, Exception Path 6 |
| **Non-JSON-Native Result Types** | `default=str` serialization ensures valid UTF-8 JSON for dates/decimals/binaries. | PRD16 |
| **Result Set Too Large** | Truncation at per-database ceiling with explicit notice (total vs returned). | PRD15, AC12 |

## Technical Checklist (Atomic Tasks)

### 🔵 Phase 1 — Domain Core (Zero framework dependencies)

#### Scaffolding & leaf nodes (fully parallel — no domain dependencies)

- [ ] Task 001 - [Scaffolding]: Initialize new repository structure, package metadata and tooling (Depends On: —)
- [ ] Task 002 - [Domain-Enum]: Create `DatabaseType` enum (Depends On: —)
- [ ] Task 003 - [Domain-Enum]: Create `SqlViolationType` enum (extended) (Depends On: —)
- [ ] Task 004 - [Domain-Exception]: Create `SqlValidationError` hierarchy (Depends On: —)
- [ ] Task 005 - [Domain-Exception]: Create `DatabaseConnectionError` hierarchy (Depends On: —)
- [ ] Task 006 - [Domain-Model]: Create `ParsedSqlStatement` value object (Depends On: —)
- [ ] Task 007 - [Domain-Model]: Create `SqlValidationResult` value object (Depends On: Task 003)
- [ ] Task 008 - [Domain-Model]: Create `DatabaseConnectionConfig` model (Depends On: Task 002)
- [ ] Task 009 - [Domain-Model]: Create `DatabaseCatalogEntry` model (Depends On: Task 002, Task 008)
- [ ] Task 010 - [Domain-Model]: Create `SensitiveColumnPolicy` model (Depends On: —)
- [ ] Task 011 - [Domain-Model]: Create `ErrorContract` value object (Depends On: Task 003)
- [ ] Task 012 - [Domain-Model]: Create `QueryResult` value object (Depends On: —)

#### Domain services (depend on models above)

- [ ] Task 013 - [Domain-Service]: Implement `SqlSecurityValidator` (extracted and generalized) (Depends On: Task 003, Task 004, Task 006, Task 007)
- [ ] Task 014 - [Domain-Service]: Implement `SensitiveDataSanitizer` (schema policy + value heuristics) (Depends On: Task 010, Task 012)
- [ ] Task 015 - [Domain-Service]: Implement `ErrorContractFactory` (Depends On: Task 004, Task 005, Task 011)

#### Phase 1 unit tests (parallel-safe, inner-testing of pure logic)

- [ ] Task 016 - [Test-Unit]: Unit tests for domain enums, models and exceptions (Depends On: Task 002, Task 003, Task 004, Task 005, Task 006, Task 007, Task 008, Task 009, Task 010, Task 011, Task 012)
- [ ] Task 017 - [Test-Unit]: Unit tests for `SqlSecurityValidator` rule matrix (Depends On: Task 013)
- [ ] Task 018 - [Test-Unit]: Adversarial unit tests for `SensitiveDataSanitizer` (Depends On: Task 014)
- [ ] Task 019 - [Test-Unit]: Unit tests for `ErrorContractFactory` (Depends On: Task 015)

### 🟡 Phase 2 — Ports & Use Cases (All tasks parallel-safe | Depends on Phase 1)

- [ ] Task 020 - [Port-Out]: Define `SqlParserPort` output port (multi-dialect) (Depends On: Task 006)
- [ ] Task 021 - [Port-Out]: Define `DatabaseConnectionPort` output port (Depends On: Task 008)
- [ ] Task 022 - [Port-Out]: Define `SchemaMetadataPort` output port (Depends On: Task 009)
- [ ] Task 023 - [Port-Out]: Define `ConnectionRegistryPort` output port (Depends On: Task 008, Task 009)
- [ ] Task 024 - [Port-In]: Define `ExecuteQueryUseCase` input port (Depends On: Task 011, Task 012)
- [ ] Task 025 - [Port-In]: Define `ListDatabasesUseCase` input port (Depends On: Task 009)
- [ ] Task 026 - [Port-In]: Define `ListTablesUseCase` input port (Depends On: Task 009)
- [ ] Task 027 - [Port-In]: Define `GetTableSchemaUseCase` input port (Depends On: Task 009)
- [ ] Task 028 - [UseCase]: Implement `ExecuteQueryService` (Depends On: Task 013, Task 014, Task 015, Task 020, Task 021, Task 023, Task 024)
- [ ] Task 029 - [UseCase]: Implement `ListDatabasesService` (Depends On: Task 023, Task 025)
- [ ] Task 030 - [UseCase]: Implement `ListTablesService` (Depends On: Task 022, Task 023, Task 026)
- [ ] Task 031 - [UseCase]: Implement `GetTableSchemaService` (Depends On: Task 022, Task 023, Task 027)

#### Phase 2 unit tests (parallel-safe, mocked ports)

- [ ] Task 032 - [Test-Unit]: Unit tests for use cases with mocked ports (Depends On: Task 028, Task 029, Task 030, Task 031)

### 🟢 Phase 3 — Adapters (All tasks parallel-safe | Depends on Phase 2)

- [ ] Task 033 - [Adapter-External]: Implement `SqlGlotParserAdapter` for 4 dialects (Depends On: Task 020)
- [ ] Task 034 - [Adapter-Persistence]: Implement `PostgresConnectionAdapter` (Depends On: Task 021, Task 022)
- [ ] Task 035 - [Adapter-Persistence]: Implement `MysqlConnectionAdapter` (Depends On: Task 021, Task 022)
- [ ] Task 036 - [Adapter-Persistence]: Implement `MssqlConnectionAdapter` (Depends On: Task 021, Task 022)
- [ ] Task 037 - [Adapter-Persistence]: Implement `OracleConnectionAdapter` (Depends On: Task 021, Task 022)
- [ ] Task 038 - [Adapter-Infra]: Implement `EnvConnectionRegistry` with fail-fast startup validation (Depends On: Task 023)
- [ ] Task 039 - [Adapter-Infra]: Implement `ConnectionFactory` (selects adapter by type/version) (Depends On: Task 034, Task 035, Task 036, Task 037)
- [ ] Task 040 - [Adapter-External]: Implement `JsonResponseSerializer` (truncation + redaction + safe JSON) (Depends On: Task 014, Task 012)
- [ ] Task 041 - [Adapter-Infra]: Implement `StructuredLoggingAdapter` (Depends On: Task 014)
- [ ] Task 042 - [Adapter-Web]: Implement `McpServerAdapter` with FastMCP (4 tools + catalog at session init) (Depends On: Task 028, Task 029, Task 030, Task 031, Task 038, Task 040, Task 041)
- [ ] Task 043 - [Config]: Create `.env.example` documenting `DB_<ALIAS>_*` blocks and limits (Depends On: Task 038)
- [ ] Task 044 - [Config]: Create `Dockerfile` (non-root, healthcheck) and CI quality gate with golden evals (Depends On: Task 042, Task 045, Task 046, Task 047)

#### Phase 3 tests (parallel-safe, per-adapter)

- [ ] Task 045 - [Test-Unit]: Unit tests for `SqlGlotParserAdapter` per dialect (Depends On: Task 033)
- [ ] Task 046 - [Test-Unit]: Unit tests for connection adapters with fixture DBs/mocks (Depends On: Task 034, Task 035, Task 036, Task 037)
- [ ] Task 047 - [Test-Unit]: Unit tests for `EnvConnectionRegistry`, `ConnectionFactory`, `JsonResponseSerializer`, `McpServerAdapter` (Depends On: Task 038, Task 039, Task 040, Task 042)

### 🔴 Phase 4 — Verification & Integration (Depends on Phase 3)

- [ ] Task 048 - [Test-Integration]: Golden evals per dialect for read-only guardrail (Depends On: Task 033, Task 013)
- [ ] Task 049 - [Test-Integration]: Golden evals for redaction (schema policy + heuristics) (Depends On: Task 014, Task 040)
- [ ] Task 050 - [Test-Integration]: End-to-end Happy Path: catalog at session init + `execute_query` (Depends On: Task 042)
- [ ] Task 051 - [Test-Integration]: End-to-end error contract: syntax error, mutation, stacked query, empty result (Depends On: Task 042)
- [ ] Task 052 - [Test-Integration]: End-to-end schema discovery (`list_tables`, `get_table_schema`) per database type (Depends On: Task 042)

## Task Detailing (Summary Tasks)

### Task 001 - [Scaffolding]: Initialize new repository structure

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 002, Task 003, Task 004, Task 005, Task 006, Task 007, Task 008, Task 009, Task 010, Task 011, Task 012
- **Objective:** Create the new `database-query-mcp-server` repository skeleton: package layout (`src/domain`, `src/application`, `src/adapter`), `pyproject.toml` (target `py311`, pytest, mypy strict, ruff), README, and CI pipeline stub.
- **Files/Path:** `database-query-mcp-server/` (repo root), `pyproject.toml`, `.github/workflows/ci.yml`
- **Reuse:** Follow the tooling pattern from `sales-agent/pyproject.toml` (pytest 8, mypy strict, ruff, line-length 100) — adapted, not imported.
- **Technical Acceptance Criteria:**
  - Repository structure mirrors hexagonal layout.
  - `pyproject.toml` defines pytest testpaths, mypy strict, ruff rules (E/W/F/I/B/UP).
  - Zero imports from `sales-agent` (AC01).
  - CI stub runs `pytest` + `ruff` + `mypy`.

### Task 002 - [Domain-Enum]: Create DatabaseType enum

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001, Task 003, Task 004, Task 005, Task 006
- **Objective:** Define the supported database families.
- **Files/Path:** `src/domain/model/database_type.py`
- **Technical Acceptance Criteria:**
  - Members: `ORACLE`, `MSSQL`, `POSTGRES`, `MYSQL`.
  - Each member exposes the sqlglot dialect name (`oracle`, `tsql`, `postgres`, `mysql`).
  - Pure Python `Enum` — zero framework imports.
  - Unit test (Task 016) validates members and dialect mapping.

### Task 003 - [Domain-Enum]: Create SqlViolationType enum (extended)

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001, Task 002, Task 004, Task 005
- **Objective:** Extend the extracted `SqlViolationType` (from `sales-agent/src/domain/model/sql_validation.py`) with connection and execution failure categories.
- **Files/Path:** `src/domain/model/sql_violation_type.py`
- **Reuse:** Controlled copy of `SqlViolationType` from [`sales-agent/src/domain/model/sql_validation.py`](file:///c:/Code/challenge_ai_engineer/src/domain/model/sql_validation.py).
- **Technical Acceptance Criteria:**
  - Members: `DISALLOWED_ROOT_OPERATION`, `FORBIDDEN_MUTATIONAL_NODE`, `FORBIDDEN_FUNCTION_CALL`, `STACKED_QUERIES_DETECTED`, `SQL_SYNTAX_ERROR`, plus `CONNECTION_ERROR`, `EXECUTION_ERROR`, `EMPTY_RESULT_SET`.
  - Each member has a human-readable `description`.
  - Pure Python — zero framework imports.

### Task 004 - [Domain-Exception]: Create SqlValidationError hierarchy

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001, Task 002, Task 003, Task 005
- **Objective:** Extract and generalize the SQL validation exception hierarchy.
- **Files/Path:** `src/domain/exception/sql_validation_exceptions.py`
- **Reuse:** Controlled copy of [`sales-agent/src/domain/exception/sql_validation_exceptions.py`](file:///c:/Code/challenge_ai_engineer/src/domain/exception/sql_validation_exceptions.py).
- **Technical Acceptance Criteria:**
  - `SqlValidationError(Exception)` base with `violation_type` and `detail`.
  - `SqlSyntaxError(SqlValidationError)`.
  - `SqlSecurityViolationError(SqlValidationError)` with `offending_node_type`.
  - Pure Python — zero framework imports.

### Task 005 - [Domain-Exception]: Create DatabaseConnectionError hierarchy

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001, Task 002, Task 003, Task 004
- **Objective:** Define connection-domain exceptions decoupled from driver libraries.
- **Files/Path:** `src/domain/exception/database_connection_exceptions.py`
- **Reuse:** Follow the exception pattern from `sales-agent/src/domain/exception/s3_exceptions.py`.
- **Technical Acceptance Criteria:**
  - `DatabaseConnectionError(Exception)` with `message: str` and optional `status_code`.
  - `UnsupportedDatabaseTypeError(DatabaseConnectionError)` for unknown types (PRD04).
  - `QueryExecutionError(Exception)` with `detail: str`.
  - Pure Python — zero driver imports.

### Task 006 - [Domain-Model]: Create ParsedSqlStatement value object

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 001, Task 002, Task 003
- **Objective:** Extract the immutable parsed-statement abstraction.
- **Files/Path:** `src/domain/model/parsed_sql_statement.py`
- **Reuse:** Controlled copy of `ParsedSqlStatement` from [`sales-agent/src/domain/model/sql_validation.py`](file:///c:/Code/challenge_ai_engineer/src/domain/model/sql_validation.py).
- **Technical Acceptance Criteria:**
  - Frozen dataclass: `root_node_type`, `all_node_types` (frozenset), `all_function_names` (frozenset), `statement_count`, `raw_sql`.
  - Pure Python — zero framework imports.

### Task 007 - [Domain-Model]: Create SqlValidationResult value object

- **Phase:** 1
- **Depends On:** Task 003
- **Parallel With:** Task 006, Task 008, Task 009, Task 010, Task 011, Task 012
- **Objective:** Extract the immutable validation outcome.
- **Files/Path:** `src/domain/model/sql_validation_result.py`
- **Reuse:** Controlled copy of `SqlValidationResult` from `sales-agent/src/domain/model/sql_validation.py`.
- **Technical Acceptance Criteria:**
  - Frozen dataclass: `is_valid`, `violation_type` (Optional), `violation_detail` (Optional), `offending_node` (Optional).
  - Factories `success()` and `violation(type, detail, node)`.
  - Pure Python — zero framework imports.

### Task 008 - [Domain-Model]: Create DatabaseConnectionConfig model

- **Phase:** 1
- **Depends On:** Task 002
- **Parallel With:** Task 006, Task 007, Task 009, Task 010
- **Objective:** Model one registered database connection.
- **Files/Path:** `src/domain/model/connection_config.py`
- **Technical Acceptance Criteria:**
  - Frozen dataclass with: `alias` (str), `type` (DatabaseType), `version` (str, reserved for PS016 Idea 17), connection params (host, port, database/schema, user, secret reference), `limits` (max_rows default 50, timeout_seconds), `description` (str), `sensitive_columns` (SensitiveColumnPolicy).
  - `secret` is a reference name, never the raw credential value (PRD04, CWE-798).
  - Pure Python — zero framework imports.

### Task 009 - [Domain-Model]: Create DatabaseCatalogEntry model

- **Phase:** 1
- **Depends On:** Task 002, Task 008
- **Parallel With:** Task 006, Task 007, Task 010
- **Objective:** Model the catalog entry delivered to the agent at session init (PRD05).
- **Files/Path:** `src/domain/model/database_catalog_entry.py`
- **Technical Acceptance Criteria:**
  - Frozen dataclass exposing: `nome` (alias), `descricao` (description), `tipo`, `versao`, `modo_acesso` (always `READ_ONLY`), `limites` (max rows, timeout), optional `schemas`.
  - Pure Python — zero framework imports.

### Task 010 - [Domain-Model]: Create SensitiveColumnPolicy model

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 006, Task 007, Task 008
- **Objective:** Model the per-database sensitive column policy (PRD12).
- **Files/Path:** `src/domain/model/sensitive_column_policy.py`
- **Technical Acceptance Criteria:**
  - Frozen dataclass: global denylist (default `password`, `token`, `api_key`, `secret`), per-database denylist, optional allowlist (opt-in columns safe to expose).
  - Pure Python — zero framework imports.

### Task 011 - [Domain-Model]: Create ErrorContract value object

- **Phase:** 1
- **Depends On:** Task 003
- **Parallel With:** Task 006, Task 007, Task 008
- **Objective:** Model the self-correctable error contract (PRD11).
- **Files/Path:** `src/domain/model/error_contract.py`
- **Technical Acceptance Criteria:**
  - Frozen dataclass: `category` (SqlViolationType), `sanitized_detail` (str), `self_correction_guidance` (str), `redacted` (bool).
  - Pure Python — zero framework imports.

### Task 012 - [Domain-Model]: Create QueryResult value object

- **Phase:** 1
- **Depends On:** —
- **Parallel With:** Task 006, Task 007, Task 008
- **Objective:** Model a sanitized, serializable query result (PRD16).
- **Files/Path:** `src/domain/model/query_result.py`
- **Technical Acceptance Criteria:**
  - Frozen dataclass: `columns` (list), `rows` (list of dicts), `total_records` (int), `returned_records` (int), `truncated` (bool), `redacted_columns` (list), `redaction_notice` (Optional[str]).
  - Pure Python — zero framework imports.

### Task 013 - [Domain-Service]: Implement SqlSecurityValidator (extracted and generalized)

- **Phase:** 1
- **Depends On:** Task 003, Task 004, Task 006, Task 007
- **Parallel With:** —
- **Objective:** Extract the deterministic read-only validation rules and generalize rule sets for the four dialects.
- **Files/Path:** `src/domain/service/sql_security_validator.py`
- **Reuse:** Controlled copy of [`sales-agent/src/domain/service/sql_security_validator.py`](file:///c:/Code/challenge_ai_engineer/src/domain/service/sql_security_validator.py).
- **Technical Acceptance Criteria:**
  - Rule 1 — Root operation in `{SELECT, WITH, UNION}` → else `DISALLOWED_ROOT_OPERATION`.
  - Rule 2 — `statement_count == 1` → else `STACKED_QUERIES_DETECTED`.
  - Rule 3 — `all_node_types` must not intersect forbidden mutational nodes (DROP/DELETE/UPDATE/INSERT/ALTER/CREATE/REPLACE/TRUNCATE/PRAGMA/ATTACH/DETACH/COPY/LOAD/INSTALL) → else `FORBIDDEN_MUTATIONAL_NODE`.
  - Rule 4 — `all_function_names` must not intersect file I/O functions → else `FORBIDDEN_FUNCTION_CALL`.
  - Unit tests (Task 017) prove dialect-agnostic behavior (AC04, AC05).

### Task 014 - [Domain-Service]: Implement SensitiveDataSanitizer

- **Phase:** 1
- **Depends On:** Task 010, Task 012
- **Parallel With:** —
- **Objective:** Implement deterministic redaction of passwords, tokens and API keys (PRD12, PRD13).
- **Files/Path:** `src/domain/service/sensitive_data_sanitizer.py`
- **Reuse:** Value-heuristic patterns inspired by `_sanitize_s3_error` (`sales-agent/src/adapter/outbound/persistence/duckdb_sales_adapter.py`) and `_sanitize_path_details` (`sales-agent/src/adapter/inbound/llm/sql_fallback_tool.py`) — re-implemented as pure domain logic.
- **Technical Acceptance Criteria:**
  - `sanitize_result(result, policy) -> QueryResult` replaces sensitive values with `[REDACTED]` and records `redacted_columns` + `redaction_notice` (fail-closed default per BR05).
  - Value heuristics detect: `Authorization:` headers, `Bearer` tokens, JWTs (`eyJ...`), prefixed keys (`AKIA`, `sk-`, `ghp_`), connection strings, session tokens — even in non-catalogued columns (AC10).
  - `sanitize_text(raw: str) -> str` reusable for logs/errors (PRD14, AC11).
  - No heuristic flags `[REDACTED]` as sensitive (idempotent).
  - Adversarial unit tests (Task 018) cover obvious and non-obvious column names and free-text secret patterns (AC09, AC10).

### Task 015 - [Domain-Service]: Implement ErrorContractFactory

- **Phase:** 1
- **Depends On:** Task 004, Task 005, Task 011
- **Parallel With:** —
- **Objective:** Build categorized, sanitized, self-correction-oriented errors for every failure mode (PRD11).
- **Files/Path:** `src/domain/service/error_contract_factory.py`
- **Technical Acceptance Criteria:**
  - Maps `SqlSyntaxError` → `SQL_SYNTAX_ERROR` (detail = first line of parse error, no stack trace).
  - Maps validation violations → categorized contract with guidance.
  - Maps connection/execution failures → `CONNECTION_ERROR` / `EXECUTION_ERROR` with credential-free detail (BR04, AC07, AC13).
  - Provides `empty_result_set()` contract with count 0 and filter-relaxation guidance (AC08).

### Task 016 - [Test-Unit]: Unit tests for domain enums, models and exceptions

- **Phase:** 1
- **Depends On:** Task 002, Task 003, Task 004, Task 005, Task 006, Task 007, Task 008, Task 009, Task 010, Task 011, Task 012
- **Parallel With:** Task 017, Task 018, Task 019
- **Objective:** Prove the pure domain constructs.
- **Files/Path:** `tests/unit/test_domain_models.py`
- **Technical Acceptance Criteria:**
  - All enums have expected members and non-empty descriptions.
  - Models are frozen/immutable; factories return correct instances.
  - Exceptions carry structured attributes; zero framework imports enforced by code review.

### Task 017 - [Test-Unit]: Unit tests for SqlSecurityValidator rule matrix

- **Phase:** 1
- **Depends On:** Task 013
- **Parallel With:** Task 016, Task 018, Task 019
- **Objective:** Prove the rule engine with synthetic `ParsedSqlStatement` fixtures (no sqlglot).
- **Files/Path:** `tests/unit/test_sql_security_validator.py`
- **Technical Acceptance Criteria:**
  - Happy path `SELECT`/`WITH`/`UNION` → valid.
  - Forbidden root (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`, `PRAGMA`, `ATTACH`, `DETACH`, `COPY`) → `DISALLOWED_ROOT_OPERATION` or `FORBIDDEN_MUTATIONAL_NODE`.
  - Nested mutation → `FORBIDDEN_MUTATIONAL_NODE`.
  - Forbidden function (`READ_CSV`, `GLOB`, `COPY`, `LOAD`, `INSTALL`) → `FORBIDDEN_FUNCTION_CALL`.
  - `statement_count = 2` → `STACKED_QUERIES_DETECTED`.
  - Parameterized matrix (`@pytest.mark.parametrize`).

### Task 018 - [Test-Unit]: Adversarial unit tests for SensitiveDataSanitizer

- **Phase:** 1
- **Depends On:** Task 014
- **Parallel With:** Task 016, Task 017, Task 019
- **Objective:** Prove redaction by schema policy and value heuristics (AC09, AC10).
- **Files/Path:** `tests/unit/test_sensitive_data_sanitizer.py`
- **Technical Acceptance Criteria:**
  - Denylisted column (`password`, `token`, `api_key`, `secret`) with arbitrary value → `[REDACTED]`.
  - Allowlisted column bypasses redaction.
  - Free-text values embedding `Bearer`, `Authorization:`, JWT, `AKIA...`, `sk-...` → redacted.
  - Idempotence: running twice yields same result; `[REDACTED]` never redacted again.
  - `sanitize_text` strips credentials from arbitrary strings (logs/errors).

### Task 019 - [Test-Unit]: Unit tests for ErrorContractFactory

- **Phase:** 1
- **Depends On:** Task 015
- **Parallel With:** Task 016, Task 017, Task 018
- **Objective:** Prove the categorized error contract (AC07, AC08).
- **Files/Path:** `tests/unit/test_error_contract_factory.py`
- **Technical Acceptance Criteria:**
  - Syntax error → `SQL_SYNTAX_ERROR` with guidance, no stack trace.
  - Violations map to correct categories.
  - Empty result → `EMPTY_RESULT_SET` contract with count 0 and guidance.
  - Connection error contract never contains credential values.

### Task 020 - [Port-Out]: Define SqlParserPort output port (multi-dialect)

- **Phase:** 2
- **Depends On:** Task 006
- **Parallel With:** Task 021, Task 022, Task 023, Task 024, Task 025, Task 026, Task 027
- **Objective:** Define the parsing boundary abstracting the concrete parser library.
- **Files/Path:** `src/application/port/outbound/sql_parser_port.py`
- **Technical Acceptance Criteria:**
  - `parse(raw_sql: str, dialect: str) -> ParsedSqlStatement`.
  - Raises `SqlSyntaxError` for malformed/empty SQL.
  - Docstring specifies the multi-dialect contract and literal-isolation responsibility (parser must not surface literal keywords as mutational nodes).
  - Unit test: interface is abstract, cannot be instantiated.

### Task 021 - [Port-Out]: Define DatabaseConnectionPort output port

- **Phase:** 2
- **Depends On:** Task 008
- **Parallel With:** Task 020, Task 022, Task 023
- **Objective:** Define the read-only connection boundary.
- **Files/Path:** `src/application/port/outbound/database_connection_port.py`
- **Technical Acceptance Criteria:**
  - `connect() -> ConnectionHandle` establishing native read-only session (PRD18).
  - `execute_read_only(query: str, timeout_seconds: float) -> list[dict]` (columns + rows).
  - `test_connection() -> bool` for startup validation.
  - `close()`.
  - Method signatures use domain types only.

### Task 022 - [Port-Out]: Define SchemaMetadataPort output port

- **Phase:** 2
- **Depends On:** Task 009
- **Parallel With:** Task 020, Task 021, Task 023
- **Objective:** Define schema discovery boundary (PRD17).
- **Files/Path:** `src/application/port/outbound/schema_metadata_port.py`
- **Technical Acceptance Criteria:**
  - `list_tables() -> list[TableMetadata]`.
  - `get_table_schema(table: str) -> list[ColumnMetadata]` with `is_sensitive` flag resolved via policy.
  - Read-only; docstring specifies native catalog queries per database type.

### Task 023 - [Port-Out]: Define ConnectionRegistryPort output port

- **Phase:** 2
- **Depends On:** Task 008, Task 009
- **Parallel With:** Task 020, Task 021, Task 022
- **Objective:** Define the registry boundary (catalog + config lookup + startup validation).
- **Files/Path:** `src/application/port/outbound/connection_registry_port.py`
- **Technical Acceptance Criteria:**
  - `available_databases() -> list[DatabaseCatalogEntry]`.
  - `get_config(alias: str) -> DatabaseConnectionConfig` raising `DatabaseConnectionError` if unknown.
  - `validate_all() -> None` (fail-fast at startup, PRD10).
  - Method signatures use domain types only.

### Task 024 - [Port-In]: Define ExecuteQueryUseCase input port

- **Phase:** 2
- **Depends On:** Task 011, Task 012
- **Parallel With:** Task 020, Task 021, Task 022, Task 023
- **Objective:** Define the `execute_query` use-case contract.
- **Files/Path:** `src/application/port/inbound/execute_query_use_case.py`
- **Technical Acceptance Criteria:**
  - `execute(alias: str, query: str) -> QueryResult` (validated, executed read-only, sanitized, truncated).
  - Raises or returns `ErrorContract` for categorized failures (PRD11).
  - Docstring specifies the full pipeline order.

### Task 025 - [Port-In]: Define ListDatabasesUseCase input port

- **Phase:** 2
- **Depends On:** Task 009
- **Parallel With:** Task 020, Task 021, Task 022, Task 023
- **Objective:** Define the `list_databases` use-case contract.
- **Files/Path:** `src/application/port/inbound/list_databases_use_case.py`
- **Technical Acceptance Criteria:**
  - `list_databases() -> list[DatabaseCatalogEntry]` (same catalog as session init, PRD06).

### Task 026 - [Port-In]: Define ListTablesUseCase input port

- **Phase:** 2
- **Depends On:** Task 009
- **Parallel With:** Task 020, Task 021, Task 022, Task 023
- **Objective:** Define the `list_tables` use-case contract.
- **Files/Path:** `src/application/port/inbound/list_tables_use_case.py`
- **Technical Acceptance Criteria:**
  - `list_tables(alias: str) -> list[TableMetadata]` read-only.
  - Unknown alias → categorized connection/execution error.

### Task 027 - [Port-In]: Define GetTableSchemaUseCase input port

- **Phase:** 2
- **Depends On:** Task 009
- **Parallel With:** Task 020, Task 021, Task 022, Task 023
- **Objective:** Define the `get_table_schema` use-case contract.
- **Files/Path:** `src/application/port/inbound/get_table_schema_use_case.py`
- **Technical Acceptance Criteria:**
  - `get_table_schema(alias: str, table: str) -> list[ColumnMetadata]` read-only, sensitive columns flagged without values (AC14).

### Task 028 - [UseCase]: Implement ExecuteQueryService

- **Phase:** 2
- **Depends On:** Task 013, Task 014, Task 015, Task 020, Task 021, Task 023, Task 024
- **Parallel With:** Task 029, Task 030, Task 031
- **Objective:** Orchestrate the deterministic pipeline: parse → validate → execute read-only → sanitize → truncate.
- **Files/Path:** `src/application/service/execute_query_service.py`
- **Reuse:** `SqlSecurityValidator` (Task 013), `SensitiveDataSanitizer` (Task 014), `ErrorContractFactory` (Task 015), parser/connection/registry ports.
- **Technical Acceptance Criteria:**
  - Resolves connection via `ConnectionRegistryPort`.
  - Parses with target dialect (`DatabaseType.dialect`).
  - Validates; any violation short-circuits before DB access (AC04, AC06).
  - Executes via `DatabaseConnectionPort.execute_read_only`; applies row ceiling + timeout (PRD15).
  - Sanitizes result via `SensitiveDataSanitizer` (AC09, AC10).
  - Returns `QueryResult` (AC08, AC12) or raises categorized `ErrorContract` (AC07).
  - Zero framework imports; constructor injection.

### Task 029 - [UseCase]: Implement ListDatabasesService

- **Phase:** 2
- **Depends On:** Task 023, Task 025
- **Parallel With:** Task 028, Task 030, Task 031
- **Objective:** Provide the catalog to tools and session init (PRD05, PRD06).
- **Files/Path:** `src/application/service/list_databases_service.py`
- **Technical Acceptance Criteria:**
  - Delegates to `ConnectionRegistryPort.available_databases()`.
  - Returns catalog entries with `nome`, `descricao`, `tipo`, `versao`, `modo_acesso`, `limites` (AC03).
  - Zero framework imports.

### Task 030 - [UseCase]: Implement ListTablesService

- **Phase:** 2
- **Depends On:** Task 022, Task 023, Task 026
- **Parallel With:** Task 028, Task 029, Task 031
- **Objective:** Provide table listing for the given database (PRD17).
- **Files/Path:** `src/application/service/list_tables_service.py`
- **Technical Acceptance Criteria:**
  - Opens connection via registry + `SchemaMetadataPort.list_tables()`.
  - Unknown alias → categorized error.
  - Zero framework imports.

### Task 031 - [UseCase]: Implement GetTableSchemaService

- **Phase:** 2
- **Depends On:** Task 022, Task 023, Task 027
- **Parallel With:** Task 028, Task 029, Task 030
- **Objective:** Provide table schema with sensitive flags (PRD17).
- **Files/Path:** `src/application/service/get_table_schema_service.py`
- **Technical Acceptance Criteria:**
  - Opens connection, calls `SchemaMetadataPort.get_table_schema(table)`.
  - Sensitive columns flagged via `SensitiveColumnPolicy` without values (AC14).
  - Zero framework imports.

### Task 032 - [Test-Unit]: Unit tests for use cases with mocked ports

- **Phase:** 2
- **Depends On:** Task 028, Task 029, Task 030, Task 031
- **Parallel With:** —
- **Objective:** Prove use-case orchestration in isolation.
- **Files/Path:** `tests/unit/test_use_cases.py`
- **Technical Acceptance Criteria:**
  - Mock ports; assert pipeline ordering for `ExecuteQueryService` (parse before validate, validate before execute, sanitize after execute).
  - Security violation never triggers DB execute (AC04).
  - Empty result and truncation produce correct `QueryResult` (AC08, AC12).
  - Unknown alias propagates categorized error.

### Task 033 - [Adapter-External]: Implement SqlGlotParserAdapter for 4 dialects

- **Phase:** 3
- **Depends On:** Task 020
- **Parallel With:** Task 034, Task 035, Task 036, Task 037, Task 038, Task 040, Task 041
- **Objective:** Implement `SqlParserPort` using `sqlglot` with per-dialect configuration (PRD08).
- **Files/Path:** `src/adapter/outbound/parser/sqlglot_parser_adapter.py`
- **Reuse:** Controlled copy of [`sales-agent/src/adapter/outbound/parser/sqlglot_parser_adapter.py`](file:///c:/Code/challenge_ai_engineer/src/adapter/outbound/parser/sqlglot_parser_adapter.py), generalized with a `dialect` parameter.
- **Technical Acceptance Criteria:**
  - `parse(raw_sql, dialect)` uses `sqlglot.parse(sql, dialect=dialect)`.
  - Extracts `root_node_type`, recursive `all_node_types`/`all_function_names`, `statement_count`.
  - Literal keywords (`'DROP_ITEM'`) never appear in `all_node_types` (BR02, AC05).
  - `ParseError` → `SqlSyntaxError` with sanitized first-line detail.
  - Handles `None`/empty statements → `SqlSyntaxError` (AC07).

### Task 034 - [Adapter-Persistence]: Implement PostgresConnectionAdapter

- **Phase:** 3
- **Depends On:** Task 021, Task 022
- **Parallel With:** Task 033, Task 035, Task 036, Task 037, Task 038
- **Objective:** Connect to PostgreSQL in native read-only mode (PRD18) and query schema metadata.
- **Files/Path:** `src/adapter/outbound/connection/postgres_connection_adapter.py`
- **Dependency Impact:** **One new justified dependency** (`psycopg[binary]` for PostgreSQL). Required per PS016 Idea 13 (four native connectors); not replaceable by existing libraries.
- **Technical Acceptance Criteria:**
  - Establishes session with `default_transaction_read_only=on` (or equivalent `SET TRANSACTION READ ONLY`).
  - `list_tables` via `information_schema.tables`; `get_table_schema` via `information_schema.columns`.
  - `test_connection()` performs `SELECT 1`.
  - Errors mapped to domain exceptions; never expose credentials.

### Task 035 - [Adapter-Persistence]: Implement MysqlConnectionAdapter

- **Phase:** 3
- **Depends On:** Task 021, Task 022
- **Parallel With:** Task 033, Task 034, Task 036, Task 037, Task 038
- **Objective:** Connect to MySQL in native read-only mode and query schema metadata.
- **Files/Path:** `src/adapter/outbound/connection/mysql_connection_adapter.py`
- **Dependency Impact:** **One new justified dependency** (`pymysql` for MySQL). Required per PS016 Idea 13.
- **Technical Acceptance Criteria:**
  - Read-only session via `START TRANSACTION READ ONLY` / `SET SESSION TRANSACTION READ ONLY`.
  - Schema metadata via `information_schema.tables/columns`.
  - `test_connection()` performs `SELECT 1`.
  - Errors mapped to domain exceptions; never expose credentials.

### Task 036 - [Adapter-Persistence]: Implement MssqlConnectionAdapter

- **Phase:** 3
- **Depends On:** Task 021, Task 022
- **Parallel With:** Task 033, Task 034, Task 035, Task 037, Task 038
- **Objective:** Connect to SQL Server with read-only posture and query schema metadata.
- **Files/Path:** `src/adapter/outbound/connection/mssql_connection_adapter.py`
- **Dependency Impact:** **One new justified dependency** (`pyodbc` or `pymssql` — decision delegated to Engineer with this ADR: choose `pymssql` for pure-Python deployment unless the target environment mandates ODBC). Required per PS016 Idea 13.
- **Technical Acceptance Criteria:**
  - Read-only posture: database user with `db_datareader`-only privileges documented; connection string enforces `ApplicationIntent=ReadOnly` where applicable (native read-only mechanisms per PRD18).
  - Schema metadata via `INFORMATION_SCHEMA.TABLES/COLUMNS`.
  - `test_connection()` performs `SELECT 1`.
  - Errors mapped to domain exceptions; never expose credentials.

### Task 037 - [Adapter-Persistence]: Implement OracleConnectionAdapter

- **Phase:** 3
- **Depends On:** Task 021, Task 022
- **Parallel With:** Task 033, Task 034, Task 035, Task 036, Task 038
- **Objective:** Connect to Oracle DB with read-only posture and query schema metadata using the Oracle Database driver.
- **Files/Path:** `src/adapter/outbound/connection/oracle_connection_adapter.py`
- **Dependency Impact:** **One new justified dependency** (`oracledb` thin mode for Oracle, with `oracledb[thin]` default and thick-mode option for older Oracle versions — aligned with PS016 Idea 17 about per-version connectors). Required per PS016 Idea 13.
- **Technical Acceptance Criteria:**
  - Session read-only via `SET TRANSACTION READ ONLY` after connect (Oracle supports read-only transactions, PRD18).
  - Schema metadata via `ALL_TABLES` / `ALL_TAB_COLUMNS` (respecting visibility of the connected user).
  - `test_connection()` performs `SELECT 1 FROM dual`.
  - Version-driven driver selection hook present (reserved for PS016 Idea 17 matrix).
  - Errors mapped to domain exceptions; never expose credentials.

### Task 038 - [Adapter-Infra]: Implement EnvConnectionRegistry with fail-fast startup validation

- **Phase:** 3
- **Depends On:** Task 023
- **Parallel With:** Task 033, Task 034, Task 035, Task 036, Task 037, Task 039, Task 040, Task 041
- **Objective:** Parse `DB_<ALIAS>_*` environment blocks and validate all connections at startup (PRD04, PRD10).
- **Files/Path:** `src/adapter/outbound/registry/env_connection_registry.py`
- **Technical Acceptance Criteria:**
  - Parses `DB_<ALIAS>_TYPE`, `DB_<ALIAS>_VERSION`, host/port/database/user, `DB_<ALIAS>_SECRET_REF` (credential reference, not literal), `DB_<ALIAS>_MAX_ROWS` (default 50), `DB_<ALIAS>_TIMEOUT` (default seconds), `DB_<ALIAS>_DESCRIPTION`, `DB_<ALIAS>_SENSITIVE_COLUMNS` (comma-separated denylist extension).
  - Unknown `TYPE` → `UnsupportedDatabaseTypeError` (BR08).
  - `validate_all()` uses `ConnectionFactory` to `test_connection()` each entry; fails fast with credential-free diagnostics (AC13).
  - `available_databases()` returns catalog entries (AC03).

### Task 039 - [Adapter-Infra]: Implement ConnectionFactory

- **Phase:** 3
- **Depends On:** Task 034, Task 035, Task 036, Task 037
- **Parallel With:** Task 038, Task 040, Task 041
- **Objective:** Select the correct connection adapter by `DatabaseType` (+ reserved `version` hook).
- **Files/Path:** `src/adapter/outbound/connection/connection_factory.py`
- **Technical Acceptance Criteria:**
  - Maps `DatabaseType` → adapter implementation.
  - Reserved `version` parameter forwarded to adapter (PS016 Idea 17 readiness).
  - Unknown type raises `UnsupportedDatabaseTypeError`.
  - Zero adapter-to-adapter cross-reference (uses only ports and config).

### Task 040 - [Adapter-External]: Implement JsonResponseSerializer

- **Phase:** 3
- **Depends On:** Task 014, Task 012
- **Parallel With:** Task 041, Task 033, Task 034, Task 035, Task 036, Task 037, Task 038
- **Objective:** Serialize `QueryResult` to the structured JSON contract (PRD16).
- **Files/Path:** `src/adapter/outbound/serializer/json_response_serializer.py`
- **Reuse:** Applies `SensitiveDataSanitizer` (Task 014) before serialization.
- **Technical Acceptance Criteria:**
  - `ensure_ascii=False`, `default=str` for non-JSON-native types (AC16, PRD16).
  - Truncation notice with total vs returned records (AC12).
  - Redaction markers included; `redacted_columns` surfaced (AC09, AC10).
  - Deterministic output for identical inputs (AC15).

### Task 041 - [Adapter-Infra]: Implement StructuredLoggingAdapter

- **Phase:** 3
- **Depends On:** Task 014
- **Parallel With:** Task 040, Task 033, Task 034, Task 035, Task 036, Task 037, Task 038
- **Objective:** Emit one structured observation record per invocation with mandatory redaction (PRD14).
- **Files/Path:** `src/adapter/outbound/observability/structured_logging_adapter.py`
- **Technical Acceptance Criteria:**
  - Records: agent/key, database alias, sanitized query, duration, status, returned rows, redaction flags.
  - Uses `SensitiveDataSanitizer.sanitize_text` for query and error text (AC11).
  - Credentials and sensitive data never written to logs (BR05, AC11).

### Task 042 - [Adapter-Web]: Implement McpServerAdapter with FastMCP

- **Phase:** 3
- **Depends On:** Task 028, Task 029, Task 030, Task 031, Task 038, Task 040, Task 041
- **Parallel With:** —
- **Objective:** Expose the four tools via MCP and deliver the catalog at session init (PRD01, PRD02, PRD05, PRD06).
- **Files/Path:** `src/adapter/inbound/mcp/mcp_server_adapter.py`
- **Dependency Impact:** Uses `mcp` (ADR-02) + `pydantic` for tool input schemas.
- **Technical Acceptance Criteria:**
  - Tools: `execute_query(database, query)`, `list_databases()`, `list_tables(database)`, `get_table_schema(database, table)` (AC02).
  - Session initialization returns the database catalog (AC03).
  - Tool handlers delegate to use cases; never call adapters directly (hexagonal rule).
  - Categorized errors serialized per `ErrorContract` without stack traces (AC07).
  - No LLM invocation in any code path (AC15).

### Task 043 - [Config]: Create .env.example

- **Phase:** 3
- **Depends On:** Task 038
- **Parallel With:** —
- **Objective:** Document the configuration contract (12-factor).
- **Files/Path:** `database-query-mcp-server/.env.example`
- **Technical Acceptance Criteria:**
  - Full `DB_<ALIAS>_*` examples for one database of each type (oracle, mssql, postgres, mysql).
  - `SECRET_REF` documented as credential reference, never literal secrets (CWE-798).
  - `MAX_ROWS`, `TIMEOUT`, `DESCRIPTION`, `SENSITIVE_COLUMNS` documented.

### Task 044 - [Config]: Create Dockerfile and CI quality gate

- **Phase:** 3
- **Depends On:** Task 042, Task 045, Task 046, Task 047
- **Parallel With:** —
- **Objective:** Package the server with non-root posture, healthcheck, and wire CI to gate on golden evals (NFR Testability, PS016 Idea 10).
- **Files/Path:** `Dockerfile`, `.github/workflows/ci.yml`
- **Reuse:** Follow `sales-agent/Dockerfile` posture (non-root `appuser`, no bytecode cache).
- **Technical Acceptance Criteria:**
  - Non-root user; `PYTHONDONTWRITEBYTECODE=1`.
  - Healthcheck hitting MCP readiness endpoint.
  - CI runs: unit tests, golden evals (Tasks 048–049), and integration tests (Tasks 050–052) as blocking gate (AC16).
  - Credentials never embedded in the image.

### Task 045 - [Test-Unit]: Unit tests for SqlGlotParserAdapter per dialect

- **Phase:** 3
- **Depends On:** Task 033
- **Parallel With:** Task 046, Task 047
- **Objective:** Prove parsing and literal isolation across the four dialects.
- **Files/Path:** `tests/unit/test_sqlglot_parser_adapter.py`
- **Technical Acceptance Criteria:**
  - For each dialect: `SELECT`/`WITH` root detection, `statement_count`, malformed SQL → `SqlSyntaxError`.
  - Literal isolation: `WHERE x = 'DROP_ITEM'` never yields `DROP` in `all_node_types` (any dialect) (AC05).
  - Stacked queries detected (`SELECT 1; DROP TABLE t` → `statement_count = 2`) (AC06).

### Task 046 - [Test-Unit]: Unit tests for connection adapters

- **Phase:** 3
- **Depends On:** Task 034, Task 035, Task 036, Task 037
- **Parallel With:** Task 045, Task 047
- **Objective:** Prove connection adapters with fixtures/mocks per database type.
- **Files/Path:** `tests/unit/test_connection_adapters.py`
- **Technical Acceptance Criteria:**
  - Read-only session flags asserted (PRD18) per type.
  - `test_connection`, `execute_read_only`, `list_tables`, `get_table_schema` map to correct native catalog queries.
  - Domain exceptions raised on driver errors; no credentials in messages.

### Task 047 - [Test-Unit]: Unit tests for registry, factory, serializer and MCP adapter

- **Phase:** 3
- **Depends On:** Task 038, Task 039, Task 040, Task 042
- **Parallel With:** Task 045, Task 046
- **Objective:** Prove infrastructure adapters in isolation.
- **Files/Path:** `tests/unit/test_infrastructure_adapters.py`
- **Technical Acceptance Criteria:**
  - `EnvConnectionRegistry` parse/fail-fast behavior with valid and invalid env fixtures (AC13).
  - `ConnectionFactory` type mapping incl. unknown type error.
  - `JsonResponseSerializer` truncation, redaction markers, `ensure_ascii=False` (AC12, AC16).
  - `McpServerAdapter` exposes 4 tools and catalog at session init (AC02, AC03).

### Task 048 - [Test-Integration]: Golden evals per dialect for read-only guardrail

- **Phase:** 4
- **Depends On:** Task 033, Task 013
- **Parallel With:** Task 049
- **Objective:** Blocking regression suite for the AST guardrail across dialects (PS016 Idea 11; AC04, AC05, AC06).
- **Files/Path:** `tests/evals/golden_guardrail/`
- **Reuse:** Golden eval concept from `sales-agent` (R010/T010) — reimplemented deterministically, not imported.
- **Technical Acceptance Criteria:**
  - Canonical valid queries with forbidden words in literals pass for all 4 dialects (AC05).
  - Mutations at root and nested depth rejected for all 4 dialects (AC04).
  - Stacked queries rejected (AC06).
  - Deterministic: identical input → identical verdict (AC15).
  - Runs as blocking quality gate in CI (AC16).

### Task 049 - [Test-Integration]: Golden evals for redaction

- **Phase:** 4
- **Depends On:** Task 014, Task 040
- **Parallel With:** Task 048
- **Objective:** Adversarial redaction suite (AC09, AC10).
- **Files/Path:** `tests/evals/golden_redaction/`
- **Technical Acceptance Criteria:**
  - Obvious and non-obvious sensitive column names redacted.
  - Real patterns (JWT, `Bearer`, `Authorization:`, `AKIA`, `sk-`) redacted in free text.
  - Logs/errors free of secrets (AC11).
  - Deterministic output.

### Task 050 - [Test-Integration]: End-to-end Happy Path (catalog + execute_query)

- **Phase:** 4
- **Depends On:** Task 042
- **Parallel With:** Task 051, Task 052
- **Objective:** Prove the full value chain with a live/fixture database (MCP host → catalog → query → sanitized result).
- **Files/Path:** `tests/integration/test_mcp_happy_path.py`
- **Technical Acceptance Criteria:**
  - MCP session init returns catalog entries with `nome`, `descricao`, `tipo`, `versao`, `modo_acesso`, `limites` (AC03).
  - `execute_query` on a fixture DB returns sanitized, truncated, structured JSON (AC09, AC12, AC16).
  - No LLM invocation anywhere (AC15).
  - Uses fixture databases or `testcontainers`/Docker DBs per type; `skipif` when unavailable.

### Task 051 - [Test-Integration]: End-to-end error contract

- **Phase:** 4
- **Depends On:** Task 042
- **Parallel With:** Task 050, Task 052
- **Objective:** Prove categorized, self-correctable errors end-to-end (AC07, AC08).
- **Files/Path:** `tests/integration/test_mcp_error_contract.py`
- **Technical Acceptance Criteria:**
  - Syntax error → `SQL_SYNTAX_ERROR` + guidance, no stack trace (AC07).
  - Mutation attempt → blocked before DB access (AC04).
  - Stacked query → rejected (AC06).
  - Empty result → `EMPTY_RESULT_SET` contract (AC08).
  - Invalid connection → credential-free diagnostic (AC13).

### Task 052 - [Test-Integration]: End-to-end schema discovery

- **Phase:** 4
- **Depends On:** Task 042
- **Parallel With:** Task 050, Task 051
- **Objective:** Prove `list_tables` and `get_table_schema` per database type (AC14).
- **Files/Path:** `tests/integration/test_mcp_schema_discovery.py`
- **Technical Acceptance Criteria:**
  - `list_tables` returns fixture tables per type.
  - `get_table_schema` returns columns with `is_sensitive` flagged and no values exposed (AC14).
  - Reads native metadata catalogs per database type.

## Parallelism Metrics

| Metric | Value |
| --- | --- |
| Total Tasks | 52 |
| Phase 1 (Domain) | 19 tasks (max 12 parallel leaf nodes) |
| Phase 2 (Ports & Use Cases) | 13 tasks (max 8 parallel) |
| Phase 3 (Adapters) | 15 tasks (max 9 parallel) |
| Phase 4 (Integration) | 5 tasks (max 3 parallel) |
| Parallelism Ratio | **75%** (39 of 52 tasks executable in parallel within phases) |

## Verification Plan

### Automated Tests

```bash
# Phase 1 — domain
python -m pytest tests/unit/test_domain_models.py tests/unit/test_sql_security_validator.py tests/unit/test_sensitive_data_sanitizer.py tests/unit/test_error_contract_factory.py -v

# Phase 2 — use cases with mocked ports
python -m pytest tests/unit/test_use_cases.py -v

# Phase 3 — adapters
python -m pytest tests/unit/test_sqlglot_parser_adapter.py tests/unit/test_connection_adapters.py tests/unit/test_infrastructure_adapters.py -v

# Phase 4 — golden evals and integration
python -m pytest tests/evals tests/integration -v

# Full suite (CI blocking gate)
python -m pytest
```

### Manual Verification

- Start the MCP server with two fixture databases of different types (e.g., PostgreSQL + MySQL), connect a real MCP host and verify the catalog at session init, a `SELECT *` over a table with `password`/`token` columns returning `[REDACTED]`, and a `DROP TABLE` attempt being blocked with categorized guidance.
- Verify `docker build` succeeds with the non-root user and that `docker run` starts cleanly with the healthcheck reporting ready.

## Finalization

- **Status:** Technical specification drafted (awaiting Quality Agent validation and Engineer Agent execution).
- **Local de entrega:** new independent repository `database-query-mcp-server/` (controlled extraction). The `sales-agent` remains untouched (PS001–PS015 immutable).
- **Scopo desta entrega:** PS016 Package 1 (Ideas 1, 2, 8, 13, 15 and 16). Authentication (Package 2), full version compatibility matrix (Package 3 Idea 17) and Docker/golden evals as packaged deliverables are partially prepared here (reserved fields, adapters, CI) and completed in subsequent packages.
- **Commit Suggestion:** `docs(architecture): specify database query MCP server core with hexagonal parallelism (T016)`
