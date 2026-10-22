# PRD: Database Query MCP Server Core (Oracle DB, SQL Server, PostgreSQL and MySQL)

## Summary

Origin: [PS016-database-query-mcp-tool.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS016-database-query-mcp-tool.md), Recommendation: Package 1 — Core Extracted (Ideas 1, 2, 8, 13, 15 and 16), Handoff: create a PRD for the database query MCP server core covering Oracle DB, SQL Server, PostgreSQL and MySQL (execute_query + database catalog on connection + self-correctable error contract + sensitive data sanitization for passwords, tokens and API keys + LLM-free deterministic validation).

The **Sales Data Analysis Agent** operates, in production, a high-value, low domain-dependency capability: the `secured_sql_query` tool. A consuming LLM writes and executes ad-hoc read-only SQL against a DuckDB database protected by three critical guarantees: deterministic structural validation via AST (`SqlSecurityValidator` + `SqlGlotParserAdapter`), strictly read-only execution with controlled error sanitization, and an error contract designed for agent self-correction (R005, R009/T009, R011/T011).

This PRD specifies the creation of a **standalone and reusable MCP (Model Context Protocol) server** that extracts that proven capability from the Sales Agent and generalizes it to **four market relational databases**: **Oracle DB**, **SQL Server**, **PostgreSQL** and **MySQL**. The product is delivered as an **independent, self-contained repository** with zero dependency on the `sales-agent` monolith (PS016, Idea 14 — Package 0). The extraction is a controlled copy of the relevant pure-domain pieces (`SqlSecurityValidator`, `ParsedSqlStatement`, `SqlSyntaxError`, sanitization patterns and error contract), generalized to the four dialects.

The server exposes the tools `execute_query`, `list_databases`, `list_tables` and `get_table_schema`, delivers the **database catalog on session initialization**, maintains the **self-correctable error contract**, applies **sensitive data sanitization** (passwords, tokens and API keys) on every response, and is **100% deterministic and LLM-free**: the query arrives fully formed from the MCP host agent, and the server only parses, validates, executes and responds.

The delivered value is an enterprise-ready, read-only database interrogation surface that bug-hunting agents (support agents, debugger agents, platform engineers, observability pipelines) can consume iteratively and safely against heterogeneous stacks, without mutation risk, without credential leakage into LLM context or logs, and with structured errors that enable full autonomous self-correction.

## Functional Requirements

- **PRD01 (Standalone MCP Server):** The system must provide a self-contained MCP server exposing the tools `execute_query`, `list_databases`, `list_tables` and `get_table_schema` through the Model Context Protocol, consumable by any MCP host (IDE, agent CLI, orchestration platforms) without reimplementation per client.
- **PRD02 (LLM-Free Deterministic Validation):** The server must not embed, invoke or suggest LLM inference. All validation must be deterministic structural analysis (AST parse + read-only guardrail per dialect) followed by read-only execution and structured response. The server must not generate SQL, suggest corrections or interpret intent.
- **PRD03 (Independent Repository and Controlled Extraction):** The implementation must live in a new, self-contained repository, containing only the extracted and generalized pieces (validation domain, per-dialect parser, connection catalog, MCP transport, golden evals and Dockerfile), with its own semantic versioning and CI/CD pipeline. Zero runtime or import dependency on any `sales-agent` module must be maintained.
- **PRD04 (Connection Registration with Type and Version):** Each registered database must declare at least a logical alias and a mandatory type (`oracle`, `mssql`, `postgres`, `mysql`), plus connection parameters, credentials, limits and a description. The data model must reserve a version field from day one (e.g., `oracle_19c`, `mssql_2019`, `postgres_15`, `mysql_8.0`) so the full version compatibility matrix (PS016, Idea 17 — Package 3) and per-version connector selection can be added without breaking the core contract.
- **PRD05 (Database Catalog at Session Initialization):** On MCP connection/session initialization, the server must deliver the catalog of available databases. Each entry must expose: `nome` (logical alias used in `execute_query`), `descrição` (business context: what it contains, when to use, table examples), `tipo` (`oracle`/`mssql`/`postgres`/`mysql`), `modo_acesso` (always read-only), `limites` (max rows, timeout) and, optionally, `versão` and `schemas` available.
- **PRD06 (`list_databases` Tool):** The system must expose a `list_databases` tool returning the same catalog delivered at session initialization, so the agent can re-query available databases on demand.
- **PRD07 (`execute_query` Tool):** The system must expose `execute_query(database, query)` applying the inherited pipeline adapted to the target database dialect: AST parse, deterministic read-only validation, read-only execution, JSON serialization, result truncation and sensitive data sanitization.
- **PRD08 (Per-Dialect AST Validation):** The AST parser must be parameterized with the dialect of the target database (Oracle, T-SQL for SQL Server, PostgreSQL, MySQL). The read-only structural rules must remain dialect-agnostic in intent: root operation restricted to `SELECT`/`WITH`/`UNION`, deep mutational node rejection (DDL and DML), file I/O function blocking, and stacked query rejection — all adapted to each dialect's grammar and conventions.
- **PRD09 (Strictly Read-Only Execution):** Each connection must operate in read-only mode from the perspective of the database itself (native read-only mechanism per database type) in addition to the AST guardrail. External access and arbitrary file/network features must be disabled whenever the database engine supports it (e.g., DuckDB `SET enable_external_access = false;` pattern inherited from the Sales Agent).
- **PRD10 (Startup Fail-Fast with Diagnostic):** The server must validate every registered connection at startup and fail fast with a clear diagnostic message when a connection is invalid, unreachable or declared with an unsupported type, without exposing credentials.
- **PRD11 (Self-Correctable Error Contract):** The system must return categorized, sanitized and self-correction-oriented errors for all failure modes: `SQL_SYNTAX_ERROR`, `DISALLOWED_ROOT_OPERATION`, `FORBIDDEN_MUTATIONAL_NODE`, `FORBIDDEN_FUNCTION_CALL`, `STACKED_QUERIES_DETECTED`, `EMPTY_RESULT_SET` and connection/execution failures. Every error must include explicit correction guidance (`self_correction_guidance`) and must never expose stack traces, paths or credentials.
- **PRD12 (Sensitive Data Sanitization by Schema):** The response serialization layer must redact values from columns declared sensitive in the database's catalog policy (per-database allowlist/denylist of columns, e.g., `password`, `token`, `api_key`, `secret`), replacing values with `[REDACTED]`.
- **PRD13 (Sensitive Data Sanitization by Value Heuristics):** The response serialization layer must also detect and redact sensitive values by value pattern heuristics even when the column is not catalogued: `Authorization:` headers, `Bearer` tokens, JWTs, prefixed keys (e.g., `AKIA`, `sk-`), connection strings and session tokens. The response must signal explicitly when redaction occurred.
- **PRD14 (Sanitized Observability):** Every invocation must emit a structured log (agent/key, database, query, duration, status, returned rows) with mandatory redaction of credentials, paths and sensitive values. Logs and error messages must never contain connection credentials (database user password, `CONNECT_STRING`, session tokens) or sensitive data returned by queries.
- **PRD15 (Controlled Truncation and Limits):** Result sets must be bounded by per-database configuration: a maximum row ceiling per query (inherited default of 50 rows from the Sales Agent), a maximum execution timeout, and explicit notice in the payload when the result was truncated (informing total vs. returned records).
- **PRD16 (Structured JSON Response):** Successful responses must be serialized as structured JSON preserving column structure and counting, with status, warnings, `self_correction_guidance` (when applicable), redaction markers and data, using UTF-8 encode with `ensure_ascii=False` and safe string conversion for non-JSON-native types (inherited pattern).
- **PRD17 (Schema Discovery on Demand):** The system must expose `list_tables(database)` and `get_table_schema(database, table)` reading native metadata catalogs per database type (Oracle, SQL Server, PostgreSQL, MySQL), returning read-only table and column metadata. Columns identified as sensitive must be flagged in schema metadata without exposing their values.
- **PRD18 (Non-Negotiable Read-Only Posture per Database Type):** For each supported type, the connection must be established with the database's native read-only mechanism where available (e.g., read-only role/user, `read_only` session modes, transaction read-only) so that even a guardrail bypass attempt cannot mutate data.

## Non-Functional Requirements

- **Determinism:** Validation and execution outcomes must be 100% reproducible: identical input yields identical output. No probabilistic, heuristic, or model-based decision may be involved in the pipeline (heuristics are admitted exclusively for value redaction in PRD13 and never for access decisions).
- **Security & Defense in Depth (CWE-200, CWE-209, CWE-532):** Sensitive data and credentials must never appear in LLM context, API responses, logs, evals or audit trails. Fail-closed default: any ambiguous redaction state must redact rather than expose.
- **Latency Budget:** AST parsing and validation must complete in under 5 ms for standard analytical queries (inherited from R005/PRD). Execution latency is bounded by per-database timeouts.
- **Portability:** The new repository must compile and run with zero imports from the `sales-agent` repository. All extracted pieces must be copied and generalized, not referenced.
- **Maintainability (Clean Architecture / Hexagonal):** The pure domain (validation rules, models, exceptions, redaction) must be framework-free and independent of the MCP transport, connection adapters and serialization adapters, maximizing parallel task execution across the architecture (hexagonal parallelism).
- **Configurability (12-Factor):** All runtime configuration (connections, keys, limits, redaction policy) must be environment-driven. Credentials must never be hardcoded or embedded in the image.
- **Testability:** Golden evals for the guardrail must cover each supported dialect, plus adversarial redaction and self-correction contract tests, as a blocking quality gate in CI before publishing any image.

## Business Rules

- **BR01 (Strict Read-Only Enforcement):** Only read-only analytical queries (`SELECT`, `WITH`/CTEs, `UNION` of `SELECT`) are permitted. Any DDL/DML operation, at any depth, must be rejected before execution.
- **BR02 (Literal Isolation):** Keywords matching DDL/DML names inside string literals, aliases or comments (e.g., `WHERE status = 'DROP_ITEM'`) must never trigger security rejections.
- **BR03 (Single Statement Constraint):** Exactly one SQL statement is allowed per execution. Multi-statement payloads separated by semicolons must be rejected prior to execution.
- **BR04 (Sanitized Error Reporting):** All error messages returned to the agent must redact host paths (`[REDACTED_PATH]`), credentials and sensitive values, and must never expose stack traces or database internals.
- **BR05 (Sanitization is Non-Negotiable):** Every response, log and error must pass through the redaction layer. The absence of a per-database sensitive column policy must default to the safe posture: global denylist plus value heuristics still apply. Sensitive values are replaced with `[REDACTED]` and the response signals redaction explicitly.
- **BR06 (Catalog is the Source of Truth):** The database catalog delivered at session initialization and via `list_databases` is the authoritative context the consuming LLM uses to decide what to query and where. It must reflect only valid, startup-validated connections.
- **BR07 (Deterministic Guardrail, Creative Client):** The agent host is the only SQL generator and is responsible for self-correction. The MCP must never generate, suggest or reinterpret SQL; it validates, executes and responds.
- **BR08 (Graceful Fail-Fast):** An invalid, unreachable or unsupported connection must produce a clear startup diagnostic (or per-call categorized error) without crashing the process and without exposing connection secrets.

## Critical Data (Conceptual)

- **Connection Registry Entry:** Logical alias, type (`oracle`, `mssql`, `postgres`, `mysql`), version, connection parameters, credentials (kept secret, never logged), per-database limits (max rows, timeout), business description, sensitive column policy (allowlist/denylist).
- **Database Catalog DTO:** `nome`, `descrição`, `tipo`, `versão` (optional), `modo_acesso` (read-only), `limites`, optional `schemas`.
- **Raw SQL Query Container:** The raw SQL text received from the MCP host for analysis and execution.
- **Parsed Statement Model:** `ParsedSqlStatement` — root node type, all node types, all function names, statement count, raw SQL.
- **Validation Outcome:** `SqlValidationResult` — `is_valid`, violation type, violation detail, offending node.
- **Error Contract Payload:** Category (e.g., `SQL_SYNTAX_ERROR`, `FORBIDDEN_MUTATIONAL_NODE`, `STACKED_QUERIES_DETECTED`, `EMPTY_RESULT_SET`), sanitized message, `self_correction_guidance`.
- **Sanitized Response Payload:** Status, total vs. returned records, truncation notice, redaction markers, sanitized data rows.
- **Observability Record:** Timestamp, agent/key, database alias, sanitized query, duration, status, returned rows, redaction flags.

## User Flow

### Happy Path (Iterative Bug-Hunting Investigation)

1. The MCP host (e.g., a debugger agent) initializes a session against the Database Query MCP Server.
2. The server delivers the **database catalog** at session initialization: databases with logical alias, business description, type, version, access mode and limits.
3. The agent reads the catalog and decides, e.g., that the alias `prod_oracle` is the analytical replica relevant to the incident.
4. The agent calls `list_tables(database="prod_oracle")` and then `get_table_schema(database="prod_oracle", table="orders")` to learn the native schema without guessing.
5. The agent generates a read-only query: `SELECT id, status, created_at FROM orders WHERE created_at >= '2026-10-01' LIMIT 50`.
6. The server parses the AST, validates read-only constraints for the Oracle dialect, executes the query in read-only mode, truncates to the configured ceiling, applies sensitive data sanitization (if any column is declared sensitive) and returns a structured JSON payload.
7. The agent analyzes the data and, if needed, issues a refined query in the next turn.
8. The server logs the invocation with mandatory redaction of credentials and sensitive values.

### Exception Path 1 (Mutational Operation Attempted)

1. The agent generates a query containing a DDL/DML operation: `DELETE FROM orders WHERE id = 42`.
2. The AST parser identifies the mutational node at any depth.
3. The validator flags the violation (`FORBIDDEN_MUTATIONAL_NODE` or `DISALLOWED_ROOT_OPERATION`).
4. Execution is halted immediately; no database call is dispatched.
5. The server returns a categorized, sanitized error with `self_correction_guidance` instructing the agent to rewrite as a read-only query.

### Exception Path 2 (Stacked Queries Injection)

1. The agent (or an injected payload) sends a stacked query: `SELECT * FROM orders; DROP TABLE orders;`.
2. The parser detects multiple statements.
3. The validator responds with `STACKED_QUERIES_DETECTED` and refuses execution.
4. The agent receives the structured error and corrects the query in the next turn.

### Exception Path 3 (Invalid SQL Syntax)

1. The agent sends malformed SQL (unmatched parentheses, invalid clause order).
2. The parser raises a syntax error.
3. The server returns `SQL_SYNTAX_ERROR` with a sanitized detail (first line of the parse error only) and a correction hint, without stack traces or internal paths.

### Exception Path 4 (Empty Result Set)

1. The query is valid and safe but returns zero rows.
2. The server returns the structured `EMPTY_RESULT_SET` payload with count `0` and `self_correction_guidance` suggesting filter relaxation checks.

### Exception Path 5 (Sensitive Data Redaction)

1. The agent executes `SELECT *` over a table containing a `password` column (denylisted globally or by per-database policy).
2. The response maintains the column structure and row count, but the sensitive values are replaced with `[REDACTED]`.
3. The response includes an explicit redaction notice, and the audit log confirms no secret was written.
4. Value heuristics also redact unexpected secrets (e.g., a `Bearer` token inside a free-text log column).

### Exception Path 6 (Startup Failure or Unsupported Connection)

1. An operator registers a database with an invalid connection string or an unsupported type.
2. The server fails fast at startup with a clear diagnostic message pinpointing the configuration issue without revealing credentials.
3. If a runtime connection drops mid-session, the server returns a categorized, sanitized connection error with guidance, and the agent can retry or select another database from the catalog.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | The new repository compiles and runs with zero imports from any `sales-agent` module. | CI dependency check and import scan. |
| AC02 | The MCP server exposes `execute_query`, `list_databases`, `list_tables` and `get_table_schema` tools consumable by a standard MCP host. | PoC: connect a real MCP host and invoke each tool. |
| AC03 | The database catalog is delivered at session initialization with `nome`, `descrição`, `tipo`, `modo_acesso` and `limites` per database. | MCP session initialization test asserting catalog payload. |
| AC04 | AST validation rejects direct and nested mutational statements for all four dialects (Oracle, T-SQL, PostgreSQL, MySQL). | Golden evals per dialect with mutational adversarial cases. |
| AC05 | Queries containing forbidden words inside string literals execute successfully without false positives in all four dialects. | Golden evals per dialect with literal isolation cases (e.g., `'DROP_ITEM'`). |
| AC06 | Multi-statement payloads are rejected before execution with `STACKED_QUERIES_DETECTED`. | Unit test with stacked query payloads. |
| AC07 | Malformed SQL returns `SQL_SYNTAX_ERROR` with sanitized detail and correction guidance, without stack traces or paths. | Unit test asserting absence of stack traces and presence of guidance. |
| AC08 | Empty result sets return the structured `EMPTY_RESULT_SET` contract with count and self-correction guidance. | Unit/integration test with a valid query returning zero rows. |
| AC09 | `SELECT *` over a table with denylisted sensitive columns returns `[REDACTED]` values and an explicit redaction notice. | Integration test with a fixture table containing `password`/`token`/`api_key` columns. |
| AC10 | Value heuristics redact `Authorization:` headers, `Bearer` tokens, JWTs and prefixed keys even in non-catalogued columns. | Adversarial redaction test with real secret patterns in free-text columns. |
| AC11 | Logs, errors and audit trails never contain connection credentials or sensitive query data. | Log capture assertion during redaction and error injection tests. |
| AC12 | Result sets are truncated to the configured per-database ceiling with a notice informing total vs. returned records. | Integration test exceeding the row limit. |
| AC13 | Each registered connection is validated at startup and an invalid connection fails fast with a clear, credential-free diagnostic. | Startup test with invalid connection fixture. |
| AC14 | Schema discovery (`list_tables`, `get_table_schema`) reads native metadata per database type and flags sensitive columns without exposing values. | Integration tests per database type with fixture schemas. |
| AC15 | No LLM inference is invoked in any server code path; the pipeline is purely deterministic. | Code review + test asserting absence of model calls and identical outputs for identical inputs. |
| AC16 | Golden evals for the guardrail, redaction and error contract run as a blocking quality gate in CI before publishing the image. | CI pipeline inspection and golden evals execution. |

## Finalization

- **Status:** Product requirements drafted (awaiting Architect Agent for technical specification and Quality Agent validation).
- **Delivery Location:** the implementation occurs in a **new, independent repository** (controlled extraction from the `sales-agent`), not in this repository. The `sales-agent` source remains untouched (PS001–PS015 immutable).
- **Dependencies:** this PRD implements PS016 Package 1 and depends on Package 0 (repository foundation and controlled extraction). Authentication (PS016 Package 2) and the full multi-database version compatibility matrix (PS016 Package 3) are specified in separate PRDs.
- **Handoff:** ready for the Architect Agent to produce the technical specification (`T` files) using hexagonal parallelism: Phase 1 domain core (validation, models, exceptions, redaction), Phase 2 ports/use cases, Phase 3 adapters (transport, per-dialect parsers, connection adapters, serialization).
