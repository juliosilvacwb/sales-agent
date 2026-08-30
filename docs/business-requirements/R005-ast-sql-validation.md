# PRD: Robust SQL Validation via AST Parsing

## Summary

Origin: [PS005-ast-sql-validation.md](file:///c:/Code/challenge_ai_engineer/docs/product-strategy/PS005-ast-sql-validation.md), Recommendation: Top Recommendation (Implement AST Parsing with SQLGlot).

The Sales Data Analysis Agent provides a Secured SQL Fallback Tool (`SecuredSQLQueryTool`) to execute ad-hoc analytical queries against DuckDB when incoming user queries cannot be satisfied by standard Domain Tools. The existing implementation relies on Regular Expression (Regex) matching and naive string inspection to block Data Manipulation Language (DML) and Data Definition Language (DDL) operations.

While effective as an initial safeguard, Regex matching operates purely at the text level without structural understanding of SQL grammar. This creates two critical operational problems:

1. **False Positives:** Legitimate analytical queries that contain prohibited words inside string literals (e.g., `WHERE product_id = 'DROP_01'` or `WHERE promotion_type = 'UPDATE_DISCOUNT'`) are erroneously rejected.
2. **False Negatives:** Complex query nesting, dialect-specific commands, or obfuscated injection payloads can potentially bypass text-based heuristics.

This PRD specifies the transition to structural Abstract Syntax Tree (AST) query validation powered by `sqlglot`. By parsing SQL statements into syntax trees and enforcing deterministic structural rules, the system guarantees 100% protection against mutational operations while eliminating false positives on analytical string literals.

## Functional Requirements

- **PRD01 (Structural AST Parsing with SQLGlot):** The system must parse all fallback SQL queries into an Abstract Syntax Tree (AST) using `sqlglot` configured for the DuckDB SQL dialect before query execution.
- **PRD02 (Root Operation Validation):** The system must inspect the root node of the parsed AST to ensure the operation is strictly a read-only analytical query (i.e., `SELECT`, `WITH` / Common Table Expressions (CTE), or `UNION` of `SELECT` statements).
- **PRD03 (Deep AST Mutational Node Rejection):** The system must recursively traverse the AST to detect and reject any DDL or DML nodes (including `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `REPLACE`, `TRUNCATE`, `PRAGMA`, `ATTACH`, `DETACH`, `COPY`, `LOAD`, `INSTALL`, and file system read functions), regardless of nesting depth or subquery position.
- **PRD04 (String Literal & Alias Preservation):** The system must permit restricted keywords when they appear exclusively within string literals, column aliases, or comments (e.g., `SELECT * FROM sales_data WHERE product_id = 'DROP_TABLE'`), completely eliminating regex false positives.
- **PRD05 (Multi-Statement / Stacked Query Blocking):** The system must parse and reject inputs that contain multiple stacked SQL statements (e.g., `SELECT 1; DROP TABLE sales_data;`), ensuring single-statement read execution.
- **PRD06 (Deterministic Error Feedback & Guidance):** When an AST validation fails due to syntax errors or disallowed operations, the system must return a structured, sanitized error message explaining the violation and prompting self-correction, without crashing or exposing raw stack traces.
- **PRD07 (Observability & Audit Logging):** The system must maintain telemetry markers (`[MISSING_TOOL]`) for ad-hoc fallback usage and emit structured warning/error logs when AST validation blocks an unauthorized query.

## Non-Functional Requirements

- **Performance & Latency Overhead:** AST parsing and traversal via `sqlglot` must complete in less than 5ms for standard analytical queries, introducing negligible latency to the overall agent execution flow.
- **Security & Determinism:** Query safety validation must be mathematically deterministic based on SQL grammar rather than probabilistic or regex-based pattern matching.
- **Maintainability & Clean Architecture:** The AST validation logic must be modularized within the inbound LLM adapter layer (`src/adapter/inbound/llm/`), adhering to Clean Code standards with clear separation between parsing, security rule evaluation, and query dispatching.
- **Compatibility:** Full backward compatibility with the existing DuckDB query execution interface (`SalesAnalysisUseCase.execute_custom_query`) and existing response formatting (empty result set warnings, result truncation up to 50 records, and sanitized error paths).

## Business Rules

- **BR01 (Strict Read-Only Enforcement):** Only read-only analytical queries whose resolved execution plan does not mutate data, alter schemas, or access the host filesystem are permitted.
- **BR02 (Literal Isolation):** Keywords matching DDL/DML names inside string constants (single-quoted strings in SQL) must never trigger security rejections.
- **BR03 (Single Statement Constraint):** Exactly one SQL statement is allowed per execution. Multi-statement payloads separated by semicolons must be rejected prior to execution.
- **BR04 (Sanitized Error Reporting):** All error messages returned to the LLM agent or client must redact host filesystem paths and avoid exposing database internal stack traces.

## Critical Data (Conceptual)

- **Raw SQL Query:** The raw text query generated by the LLM agent during tool invocation.
- **AST Root Node & Expression Tree:** Hierarchical representation of the parsed SQL grammar nodes.
- **Security Violation Metadata:** Classification of the violation (e.g., `DISALLOWED_ROOT_OPERATION`, `FORBIDDEN_MUTATIONAL_NODE`, `STACKED_QUERIES_DETECTED`, `SQL_SYNTAX_ERROR`) and the offending node type.
- **Sanitized Execution Result:** Serialized JSON payload returned to the LLM containing query results or self-correction guidance.

## User Flow

### Happy Path (Analytical Query with Keyword in Literal)

1. The LLM agent receives an ad-hoc analytical request (e.g., "Find sales records where product description contains 'Drop'").
2. The LLM generates the SQL fallback query: `SELECT * FROM sales_data WHERE product_id = 'DROP_ITEM'`.
3. `SecuredSQLQueryTool` invokes `sqlglot` parser with the DuckDB dialect.
4. The system inspects the AST root node (`Select`) and verifies all child nodes contain no mutational expressions.
5. The system confirms `'DROP_ITEM'` is a literal string node (`Literal`) and marks the query as safe.
6. The query executes against DuckDB via `SalesAnalysisUseCase.execute_custom_query`.
7. The tool formats the result set as a JSON payload and returns it to the agent.

### Exception Path 1 (Mutational Operation Attempted)

1. The LLM (or a malicious prompt injection) generates a query containing a DDL/DML operation: `DROP TABLE sales_data`.
2. The AST parser identifies the root node as `Drop` (or detects a nested mutational statement).
3. The AST security validator flags the violation (`FORBIDDEN_MUTATIONAL_NODE`).
4. The execution is halted immediately; no database call is dispatched.
5. A structured security error message is logged and returned: `"Erro de Segurança: A instrução 'DROP' é proibida. Apenas consultas analíticas de leitura (SELECT/WITH) são permitidas."`

### Exception Path 2 (Stacked Queries Injection)

1. The LLM generates a stacked query payload: `SELECT * FROM sales_data; DELETE FROM sales_data WHERE 1=1;`.
2. The AST parser identifies multiple statements in the input string.
3. The validator halts execution due to `STACKED_QUERIES_DETECTED`.
4. The tool returns an explicit error message rejecting multi-statement executions.

### Exception Path 3 (Invalid SQL Syntax)

1. The LLM generates malformed SQL syntax (e.g., unmatched parentheses or invalid clause ordering).
2. The `sqlglot` parser raises a `ParseError`.
3. The tool catches the parse exception, formats a self-correction hint for the LLM, and returns a sanitized error message without unhandled exceptions.

## Acceptance Criteria

| ID | Criterion | Validation Method |
| --- | --- | --- |
| AC01 | `sqlglot` is added as a project dependency and integrated into `SecuredSQLQueryTool`. | Dependency check and import validation in test suite. |
| AC02 | Analytical queries containing forbidden keywords in string literals (e.g., `WHERE product_id = 'DROP_A'`) execute successfully without false positives. | Unit test with parameterized queries containing `'DROP'`, `'DELETE'`, `'UPDATE'` in string values. |
| AC03 | Direct and nested mutational statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`, `PRAGMA`, `ATTACH`, `DETACH`, `COPY`) are structurally blocked. | Automated unit test suite asserting `use_case.execute_custom_query` is not invoked for DDL/DML inputs. |
| AC04 | Multi-statement inputs separated by semicolons are rejected before reaching DuckDB. | Unit test verifying rejection of stacked queries. |
| AC05 | Complex valid queries utilizing CTEs (`WITH ... SELECT`), aggregations, subqueries, and window functions are parsed and executed correctly. | Unit test with valid multi-clause SQL analytics queries. |
| AC06 | Malformed SQL queries return a structured error message with self-correction guidance without raising unhandled exceptions. | Unit test evaluating graceful handling of invalid SQL syntax. |
| AC07 | Observability logging (`[MISSING_TOOL]`) and path sanitization (`[REDACTED_PATH]`) remain fully functional. | Unit tests asserting logger output and exception sanitization. |
