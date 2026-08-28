"""Unit test reproduction file for Incident B004: SQL Fallback Schema Enrichment & Validation."""
import json
from unittest.mock import MagicMock
import pytest

from src.adapter.inbound.llm.sql_fallback_tool import SecuredSQLQueryTool, SQLQueryInput, create_sql_fallback_tool
from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase


def test_sql_fallback_schema_enrichment_and_validation_reproduction():
    """
    Automated Reproduction Test for B004 - SQL Fallback Schema Enrichment & Validation.
    Validates that:
    1. SecuredSQLQueryTool input schema contains explicit DuckDB table context (promotion_type IS NULL handling, revenue meta rules).
    2. SecuredSQLQueryTool tool description includes schema context.
    3. Fallback tool provides a structured warning payload for empty result sets prompting self-correction.
    """
    # 1. Verify schema description enrichment in SQLQueryInput
    input_schema = SQLQueryInput.model_json_schema() if hasattr(SQLQueryInput, "model_json_schema") else SQLQueryInput.schema()
    query_description = input_schema.get("properties", {}).get("query", {}).get("description", "")

    assert "promotion_type" in query_description.lower(), (
        "SQLQueryInput description must include schema context for promotion_type."
    )
    assert "having count(promotion_type) = 0" in query_description.lower() or "is null" in query_description.lower(), (
        "SQLQueryInput description must explain how to query non-promoted products."
    )
    assert "actual_quantity * actual_price" in query_description.lower() or "receita" in query_description.lower(), (
        "SQLQueryInput description must include revenue calculation guidance."
    )

    # 2. Verify tool description enrichment
    mock_usecase = MagicMock(spec=SalesAnalysisUseCase)
    tool = create_sql_fallback_tool(mock_usecase)
    
    assert "promotion_type" in tool.description.lower(), (
        "SecuredSQLQueryTool description must contain schema context for promotion_type."
    )

    # 3. Verify structured warning payload for empty result set
    mock_usecase.execute_custom_query.return_value = []
    empty_result = tool.invoke({"query": "SELECT product_id FROM sales_data WHERE product_id = 'NON_EXISTENT'"})
    
    assert "EMPTY_RESULT_SET" in empty_result or "self_correction_guidance" in empty_result, (
        "SecuredSQLQueryTool must return a structured warning payload on empty results to guide self-correction."
    )


def test_sql_query_input_schema_has_full_domain_context():
    """TEST004-02: Verify SQLQueryInput.query field description contains column definitions and domain rules."""
    input_schema = SQLQueryInput.model_json_schema() if hasattr(SQLQueryInput, "model_json_schema") else SQLQueryInput.schema()
    query_description = input_schema.get("properties", {}).get("query", {}).get("description", "")
    
    for col in ["product_id", "local", "date", "planned_quantity", "actual_quantity", "planned_price", "actual_price", "service_level", "promotion_type"]:
        assert col in query_description, f"Field '{col}' must be present in SQLQueryInput query description."

    assert "HAVING COUNT(promotion_type) = 0" in query_description or "promotion_type IS NULL" in query_description
    assert "SUM(actual_quantity * actual_price)" in query_description


def test_secured_sql_tool_description_has_table_and_revenue_semantics():
    """TEST004-03: Verify tool description exposes column list and non-promoted revenue target calculation rules."""
    mock_usecase = MagicMock(spec=SalesAnalysisUseCase)
    tool = create_sql_fallback_tool(mock_usecase)

    assert "sales_data" in tool.description
    assert "promotion_type" in tool.description
    assert "SUM(actual_quantity * actual_price)" in tool.description or "Receita Realizada" in tool.description


def test_secured_sql_tool_returns_structured_warning_on_empty_results():
    """TEST004-04: When DuckDB query returns [], tool returns a JSON payload with status EMPTY_RESULT_SET."""
    mock_usecase = MagicMock(spec=SalesAnalysisUseCase)
    mock_usecase.execute_custom_query.return_value = []
    tool = create_sql_fallback_tool(mock_usecase)

    response_str = tool.invoke({"query": "SELECT * FROM sales_data WHERE product_id = 'UNKNOWN'"})
    payload = json.loads(response_str)

    assert payload["status"] == "EMPTY_RESULT_SET"
    assert payload["count"] == 0
    assert "self_correction_guidance" in payload
    assert payload["data"] == []


def test_secured_sql_tool_handles_exceptions_gracefully():
    """TEST004-05: When DuckDB query raises an Exception, verify error string is returned without crashing."""
    mock_usecase = MagicMock(spec=SalesAnalysisUseCase)
    mock_usecase.execute_custom_query.side_effect = RuntimeError("Table not found")
    tool = create_sql_fallback_tool(mock_usecase)

    response_str = tool.invoke({"query": "SELECT * FROM non_existent_table"})

    assert response_str.startswith("Erro ao executar a consulta SQL: Table not found")


def test_secured_sql_tool_sanitizes_file_paths_in_exceptions():
    """S004-01: Verify that raw file paths are sanitized in exception outputs."""
    mock_usecase = MagicMock(spec=SalesAnalysisUseCase)
    mock_usecase.execute_custom_query.side_effect = RuntimeError("Could not open file c:/Code/challenge_ai_engineer/secret.csv")
    tool = create_sql_fallback_tool(mock_usecase)

    response_str = tool.invoke({"query": "SELECT * FROM sales_data"})

    assert "c:/Code/challenge_ai_engineer/secret.csv" not in response_str
    assert "[REDACTED_PATH]" in response_str


def test_secured_sql_tool_blocks_internal_semicolons_stacked_queries():
    """S004-02: Verify that queries containing internal semicolons are blocked."""
    mock_usecase = MagicMock(spec=SalesAnalysisUseCase)
    tool = create_sql_fallback_tool(mock_usecase)

    response_str = tool.invoke({"query": "SELECT * FROM sales_data; SELECT * FROM sales_data"})

    mock_usecase.execute_custom_query.assert_not_called()
    assert "Instruções múltiplas" in response_str or "Erro de Segurança" in response_str



