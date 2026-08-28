# S004-sql-fallback-schema-enrichment — Security Audit

> **Source Task:** [B004-sql-fallback-schema-enrichment.md](../incidents/B004-sql-fallback-schema-enrichment.md)

## Security Overview

Security analysis of `SecuredSQLQueryTool` schema enrichment, DML/DDL protection mechanisms, prompt injection resilience, and structured empty result payload handling.

## Vulnerability Log

| ID | Vulnerability | Severity | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- |
| S004-01 | Internal Path / System Error Leakage in Exception Handling | Low | Low x Low | Minor information disclosure of local environment path details in raw DuckDB exception strings. |
| S004-02 | Stacked Query Semicolon Bypass Risk | Low | Low x Low | Potential execution of multiple queries if internal semicolons are unhandled. |

## Refinement Tasks

### Task 002 — Enrich SQLQueryInput and SecuredSQLQueryTool schema descriptions

- [COMPLETED] [S004-01] [Low] **Internal Error Path Sanitization**
  - **Location:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Risk:** Raw DuckDB exception messages in catch block `return f"Erro ao executar a consulta SQL: {str(e)}"` could disclose system file paths.
  - **Fix:** Sanitize exception message to strip file system path details before returning to LLM agent.
  - **Validation:** Unit test verifying exception message does not disclose full local directory path string.

### Task 003 — Structured warning payload for empty result sets

- [COMPLETED] [S004-02] [Low] **Stacked Query Semicolon Check**
  - **Location:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Risk:** Middle semicolons `;` in custom queries could allow stacked query attempts.
  - **Fix:** Reject queries containing internal semicolons (`;`) after stripping trailing whitespace and trailing semicolons.
  - **Validation:** Unit test attempting `SELECT 1; SELECT 2` verifying request rejection.
