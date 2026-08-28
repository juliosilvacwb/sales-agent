# Incident Summary

- **Test Coverage:** [TEST004-sql-fallback-schema-enrichment.md](../tests/TEST004-sql-fallback-schema-enrichment.md)
- **Security Audit:** [S004-sql-fallback-schema-enrichment.md](../security/S004-sql-fallback-schema-enrichment.md)

When users ask ad-hoc analytical questions not covered by fixed Domain Tools (such as *"Which products had no promotional sales but still met their revenue goal?"*), the fallback tool `SecuredSQLQueryTool` generates incorrect SQL queries. The LLM then erroneously responds that 0 products met the criteria, when in fact **914 products** in `dataset/sales.csv` fulfill the condition.

## Technical Analysis of Root Cause

The failure occurs due to two major limitations in `src/adapter/inbound/llm/sql_fallback_tool.py`:

1. **Lack of Schema & Domain Semantics in Tool Description:**
   The `SQLQueryInput` schema and `SecuredSQLQueryTool` description only state generic text (*"Executa uma consulta SQL analítica na tabela sales_data"*). They lack critical schema details:
   - `promotion_type` is `NULL` for 99.99% of non-promoted rows.
   - Filtering non-promoted products at the product level requires `GROUP BY product_id HAVING COUNT(promotion_type) = 0` or `WHERE promotion_type IS NULL`, rather than filtering row-level promotional items incorrectly.
   - Revenue meta achievement requires comparing `SUM(actual_quantity * actual_price) >= SUM(planned_quantity * planned_price)`.

2. **Passive Empty Result Output & Lack of Self-Correction:**
   When an ill-formed SQL query executes and returns `[]` (0 rows), `SecuredSQLQueryTool._run()` returns a passive message (*"A consulta foi executada com sucesso, mas não retornou nenhum registro"*). Seeing 0 records, the LLM accepts the result as ground truth and hallucinates an inverted conclusion ("no products met the goal without promotions").

## Reproduction Script (MANDATORY)

```python
import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService
from src.application.service.sales_metrics_service import SalesMetricsApplicationService
from src.adapter.inbound.llm.sql_fallback_tool import SecuredSQLQueryTool, SQLQueryInput


def test_sql_fallback_schema_enrichment_and_validation_reproduction():
    """
    Automated Reproduction Test for B004 - SQL Fallback Schema Enrichment & Validation.
    Validates that:
    1. SecuredSQLQueryTool input schema contains explicit DuckDB table context (promotion_type IS NULL handling, revenue meta rules).
    2. Fallback tool enforces semantic validation and enriched schema guidance.
    """
    # 1. Verify schema description enrichment in SQLQueryInput
    input_schema = SQLQueryInput.model_json_schema() if hasattr(SQLQueryInput, "model_json_schema") else SQLQueryInput.schema()
    description = input_schema.get("properties", {}).get("query", {}).get("description", "")

    assert "promotion_type" in description.lower(), (
        "SQLQueryInput description must include schema context for promotion_type."
    )
    assert "having count(promotion_type) = 0" in description.lower() or "is null" in description.lower(), (
        "SQLQueryInput description must explain how to query non-promoted products."
    )
```

## Correction Checklist (Atomic Tasks)

- [COMPLETED] Task 001 - [Test] Implement the reproduction script in `tests/unit/test_sql_fallback_incident_b004.py` and confirm the failure (Red).
- [COMPLETED] Task 002 - [Logic] Enrich `SQLQueryInput` and `SecuredSQLQueryTool` in `src/adapter/inbound/llm/sql_fallback_tool.py` with explicit `sales_data` schema context, column definitions, `promotion_type IS NULL` semantics, and calculation guidance for revenue targets.
- [COMPLETED] Task 003 - [Security/Perf] Add semantic intent validation and structured warning payload for empty result sets in `SecuredSQLQueryTool._run()` to prompt agent self-correction before returning empty results.
