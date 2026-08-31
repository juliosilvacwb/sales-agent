"""Unit tests for SecuredSQLQueryTool and observability logging."""
import logging
from unittest.mock import MagicMock
import pytest

from src.adapter.inbound.llm.sql_fallback_tool import (
    SecuredSQLQueryTool,
    create_sql_fallback_tool,
)
from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase


@pytest.fixture
def mock_sales_usecase():
    usecase = MagicMock(spec=SalesAnalysisUseCase)
    usecase.execute_custom_query.return_value = [
        {"local": "Whse_A", "total_sales": 1200.0},
        {"local": "Whse_B", "total_sales": 800.0},
    ]
    return usecase


def test_secured_sql_tool_valid_select(mock_sales_usecase, caplog):
    """Test that a valid SELECT query executes successfully and emits [MISSING_TOOL] log."""
    tool = create_sql_fallback_tool(mock_sales_usecase)
    query = "SELECT local, SUM(actual_quantity) FROM sales_data GROUP BY local"

    with caplog.at_level(logging.INFO):
        result = tool.invoke({"query": query})

    mock_sales_usecase.execute_custom_query.assert_called_once_with(query)
    assert "Whse_A" in result
    assert "1200.0" in result
    assert "[MISSING_TOOL]" in caplog.text


def test_secured_sql_tool_valid_with_select(mock_sales_usecase, caplog):
    """Test that a CTE WITH query executes successfully and emits [MISSING_TOOL] log."""
    tool = create_sql_fallback_tool(mock_sales_usecase)
    query = "WITH aggregated AS (SELECT local, actual_quantity FROM sales_data) SELECT * FROM aggregated"

    with caplog.at_level(logging.INFO):
        result = tool.invoke({"query": query})

    mock_sales_usecase.execute_custom_query.assert_called_once_with(query)
    assert "[MISSING_TOOL]" in caplog.text


@pytest.mark.parametrize(
    "forbidden_query",
    [
        "DROP TABLE sales_data",
        "DELETE FROM sales_data WHERE product_id = 'P1'",
        "UPDATE sales_data SET actual_price = 0",
        "INSERT INTO sales_data VALUES ('P1', 'L1', '2023-01-01', 1, 1, 1, 1, 1, 'none')",
        "ATTACH 'other.db' AS other",
        "DETACH other",
        "COPY sales_data TO 'out.csv'",
        "ALTER TABLE sales_data DROP COLUMN local",
        "CREATE TABLE fake_table (id INT)",
        "TRUNCATE TABLE sales_data",
        "SELECT * FROM sales_data; DROP TABLE sales_data;",
        "SELECT * FROM read_text('.env')",
        "SELECT * FROM read_csv('/etc/passwd')",
        "SELECT * FROM read_blob('secret.bin')",
        "SELECT * FROM read_parquet('data.parquet')",
        "SELECT * FROM read_json('config.json')",
        "SELECT * FROM glob('/*')",
        "INSTALL httpfs",
        "LOAD httpfs",
    ],
)
def test_secured_sql_tool_blocks_dml_ddl(mock_sales_usecase, forbidden_query):
    """Test that DML and DDL commands are blocked without executing on the usecase."""
    tool = create_sql_fallback_tool(mock_sales_usecase)
    result = tool.invoke({"query": forbidden_query})

    mock_sales_usecase.execute_custom_query.assert_not_called()
    assert "Error" in result or "Erro" in result or "SecurityViolation" in result or "Violacao de seguranca" in result or "Forbidden" in result.lower() or "blocked" in result.lower() or "rejeitada" in result.lower()


def test_secured_sql_tool_truncates_large_results():
    """Test that query result sets exceeding 50 records are truncated with metadata header."""
    mock_usecase = MagicMock(spec=SalesAnalysisUseCase)
    mock_usecase.execute_custom_query.return_value = [{"product_id": f"P_{i}"} for i in range(100)]
    
    tool = create_sql_fallback_tool(mock_usecase)
    result = tool.invoke({"query": "SELECT product_id FROM sales_data"})

    assert "total_records" in result
    assert "100" in result
    assert "50" in result


@pytest.mark.parametrize(
    "safe_query_with_literal",
    [
        "SELECT * FROM sales_data WHERE product_id = 'DROP_A'",
        "SELECT * FROM sales_data WHERE promotion_type = 'UPDATE_DISCOUNT'",
        "SELECT * FROM sales_data WHERE local = 'DELETE_ZONE'",
        "SELECT * FROM sales_data WHERE local = 'INSERT_CO'",
    ]
)
def test_secured_sql_tool_false_positive_elimination(mock_sales_usecase, safe_query_with_literal):
    """Test AC02: Queries containing forbidden keywords inside string literals execute successfully."""
    tool = create_sql_fallback_tool(mock_sales_usecase)
    result = tool.invoke({"query": safe_query_with_literal})
    
    mock_sales_usecase.execute_custom_query.assert_called_once_with(safe_query_with_literal)
    # Result shouldn't be a security error
    assert "Erro de Segurança" not in result


def test_secured_sql_tool_complex_queries(mock_sales_usecase):
    """Test AC05: Complex valid queries with CTEs, subqueries, and window functions parse and execute."""
    tool = create_sql_fallback_tool(mock_sales_usecase)
    query = """
    WITH stats AS (
        SELECT local, AVG(actual_quantity) OVER (PARTITION BY product_id) as avg_q
        FROM sales_data
    )
    SELECT * FROM stats WHERE local IN (SELECT local FROM sales_data WHERE actual_price > 100)
    """
    result = tool.invoke({"query": query})
    
    # Strip whitespace to compare the cleaned query exactly as the tool does
    mock_sales_usecase.execute_custom_query.assert_called_once_with(query.strip().rstrip(";"))
    assert "Erro de Segurança" not in result


def test_secured_sql_tool_malformed_sql(mock_sales_usecase):
    """Test AC06: Malformed SQL returns structured self-correction guidance without unhandled exceptions."""
    tool = create_sql_fallback_tool(mock_sales_usecase)
    # Missing closing parenthesis
    query = "SELECT * FROM (SELECT local FROM sales_data"
    result = tool.invoke({"query": query})
    
    mock_sales_usecase.execute_custom_query.assert_not_called()
    assert "Erro de Sintaxe" in result
    assert "corrija a sintaxe" in result


def test_secured_sql_tool_raises_tool_exception_on_syntax_error(mock_sales_usecase):
    """Test that _run raises ToolException on syntax errors (AC01)."""
    from langchain_core.tools import ToolException
    tool = create_sql_fallback_tool(mock_sales_usecase)
    with pytest.raises(ToolException) as exc_info:
        tool._run("SELECT * FROM (SELECT local FROM sales_data")
    assert "Erro de Sintaxe" in str(exc_info.value)


def test_secured_sql_tool_raises_tool_exception_on_security_violation(mock_sales_usecase):
    """Test that _run raises ToolException on security violations (AC01)."""
    from langchain_core.tools import ToolException
    tool = create_sql_fallback_tool(mock_sales_usecase)
    with pytest.raises(ToolException) as exc_info:
        tool._run("DROP TABLE sales_data")
    assert "Erro de Segurança" in str(exc_info.value)


def test_secured_sql_tool_raises_tool_exception_on_execution_error(mock_sales_usecase):
    """Test that _run raises ToolException on database query errors with sanitization (AC01, BR04)."""
    from langchain_core.tools import ToolException
    mock_sales_usecase.execute_custom_query.side_effect = RuntimeError(
        "Binder Error: Column 'total_revenue' does not exist in path c:/Code/challenge_ai_engineer/data.parquet"
    )
    tool = create_sql_fallback_tool(mock_sales_usecase)
    with pytest.raises(ToolException) as exc_info:
        tool._run("SELECT SUM(total_revenue) FROM sales_data")
    
    assert "Erro ao executar a consulta SQL" in str(exc_info.value)
    assert "[REDACTED_PATH]" in str(exc_info.value)
    assert "c:/Code/challenge_ai_engineer" not in str(exc_info.value)


def test_secured_sql_tool_handle_tool_error_attribute(mock_sales_usecase):
    """Test that SecuredSQLQueryTool defines handle_tool_error = True."""
    tool = create_sql_fallback_tool(mock_sales_usecase)
    assert tool.handle_tool_error is not None
    assert tool.handle_tool_error is True or callable(tool.handle_tool_error)


def test_secured_sql_tool_sanitizes_posix_and_windows_paths(mock_sales_usecase):
    """Test that _run sanitizes POSIX, Windows, and UNC file paths (S009-02)."""
    from langchain_core.tools import ToolException
    from src.adapter.inbound.llm.sql_fallback_tool import _sanitize_path_details

    err_posix = "IO Error: Failed to open file /var/data/sales/dataset.parquet: Permission denied"
    sanitized_posix = _sanitize_path_details(err_posix)
    assert "/var/data/sales/dataset.parquet" not in sanitized_posix
    assert "[REDACTED_PATH]" in sanitized_posix

    err_win = "IO Error: Cannot access D:\\CompanyData\\Sales\\dataset.parquet"
    sanitized_win = _sanitize_path_details(err_win)
    assert "D:\\CompanyData\\Sales\\dataset.parquet" not in sanitized_win
    assert "[REDACTED_PATH]" in sanitized_win


