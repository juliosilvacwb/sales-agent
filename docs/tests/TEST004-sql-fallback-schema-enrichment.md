# TEST004-sql-fallback-schema-enrichment — Test Coverage Specification

> **Source Task:** [B004-sql-fallback-schema-enrichment.md](../incidents/B004-sql-fallback-schema-enrichment.md)

## Coverage Overview

Validation suite for Incident B004 covering schema enrichment, domain semantic guidance (`promotion_type IS NULL`, revenue targets), and structured empty result payload handling in `SecuredSQLQueryTool`.

## Test Checklist

### Task 001 — Implement reproduction script for B004

- [COMPLETED] [TEST004-01] [Type: Unit] **test_sql_fallback_schema_enrichment_and_validation_reproduction**
  - **Target:** `tests/unit/test_sql_fallback_incident_b004.py` → `test_sql_fallback_schema_enrichment_and_validation_reproduction()`
  - **Scenario:** Validates schema description enrichment, tool description enrichment, and structured warning payload on empty result sets.
  - **Arrange:** Instantiate `SQLQueryInput` schema and `SecuredSQLQueryTool` with a mocked `SalesAnalysisUseCase`.
  - **Act:** Extract JSON schema of `SQLQueryInput`, read `SecuredSQLQueryTool.description`, and invoke tool with a query returning `[]`.
  - **Assert:** Verify `promotion_type`, `is null` / `having count`, and revenue calculation guidance exist in schema & tool descriptions, and response contains `EMPTY_RESULT_SET` and `self_correction_guidance`.
  - **Priority:** P0

### Task 002 — Enrich SQLQueryInput and SecuredSQLQueryTool schema descriptions

- [COMPLETED] [TEST004-02] [Type: Unit] **test_sql_query_input_schema_has_full_domain_context**
  - **Target:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SQLQueryInput`
  - **Scenario:** Verify `SQLQueryInput.query` field description contains all column definitions and domain rules.
  - **Arrange:** Access `SQLQueryInput.model_json_schema()` (or `.schema()`).
  - **Act:** Read the `description` string of property `query`.
  - **Assert:** Ensure description contains `product_id`, `local`, `date`, `planned_quantity`, `actual_quantity`, `planned_price`, `actual_price`, `service_level`, `promotion_type`, `HAVING COUNT(promotion_type) = 0`, and `SUM(actual_quantity * actual_price)`.
  - **Priority:** P0

- [COMPLETED] [TEST004-03] [Type: Unit] **test_secured_sql_tool_description_has_table_and_revenue_semantics**
  - **Target:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool`
  - **Scenario:** Verify tool description exposes column list and non-promoted revenue target calculation rules to the LLM agent.
  - **Arrange:** Instantiate `SecuredSQLQueryTool` via factory `create_sql_fallback_tool`.
  - **Act:** Read `tool.description`.
  - **Assert:** Ensure description includes column schema, `promotion_type IS NULL` guidance, and `SUM(actual_quantity * actual_price) >= SUM(planned_quantity * planned_price)`.
  - **Priority:** P1

### Task 003 — Structured warning payload for empty result sets

- [COMPLETED] [TEST004-04] [Type: Unit] **test_secured_sql_tool_returns_structured_warning_on_empty_results**
  - **Target:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Scenario:** When DuckDB query returns empty list `[]`, the tool returns a JSON payload with `status: EMPTY_RESULT_SET` and self-correction guidance.
  - **Arrange:** Mock `use_case.execute_custom_query` to return `[]`.
  - **Act:** Invoke `tool.invoke({"query": "SELECT * FROM sales_data WHERE product_id = 'UNKNOWN'"})`.
  - **Assert:** Parse JSON response, assert `status == 'EMPTY_RESULT_SET'`, `count == 0`, and `self_correction_guidance` is present in payload.
  - **Priority:** P0

- [COMPLETED] [TEST004-05] [Type: Unit] **test_secured_sql_tool_handles_exceptions_gracefully**
  - **Target:** `src/adapter/inbound/llm/sql_fallback_tool.py` → `SecuredSQLQueryTool._run()`
  - **Scenario:** When DuckDB query raises an Exception, verify exception string is returned without crashing the tool.
  - **Arrange:** Mock `use_case.execute_custom_query` to raise `RuntimeError("Table not found")`.
  - **Act:** Invoke `tool.invoke({"query": "SELECT * FROM non_existent_table"})`.
  - **Assert:** Assert returned string starts with `Erro ao executar a consulta SQL: Table not found`.
  - **Priority:** P1
