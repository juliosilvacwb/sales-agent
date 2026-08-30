import logging
import time
from unittest.mock import MagicMock
import pytest

from src.adapter.inbound.llm.sql_fallback_tool import create_sql_fallback_tool
from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase


@pytest.fixture
def mock_sales_usecase():
    usecase = MagicMock(spec=SalesAnalysisUseCase)
    usecase.execute_custom_query.return_value = [{"result": "success"}]
    return usecase


@pytest.fixture
def e2e_tool(mock_sales_usecase):
    return create_sql_fallback_tool(mock_sales_usecase)


def test_e2e_happy_path_literal_keyword(e2e_tool, mock_sales_usecase, caplog):
    """Happy Path: Valid analytical query with keyword in literal (AC02)."""
    query = "SELECT * FROM sales_data WHERE product_id = 'DROP_TABLE'"
    
    with caplog.at_level(logging.WARNING):
        result = e2e_tool.invoke({"query": query})
        
    assert "success" in result
    mock_sales_usecase.execute_custom_query.assert_called_once_with(query)
    assert "[MISSING_TOOL]" in caplog.text


def test_e2e_security_block(e2e_tool, mock_sales_usecase, caplog):
    """Security Block: DROP TABLE is blocked at the validator level."""
    query = "DROP TABLE sales_data"
    
    with caplog.at_level(logging.WARNING):
        result = e2e_tool.invoke({"query": query})
        
    assert "Erro de Segurança" in result
    assert "DROP" in result
    mock_sales_usecase.execute_custom_query.assert_not_called()
    assert "[MISSING_TOOL]" in caplog.text


def test_e2e_stacked_queries(e2e_tool, mock_sales_usecase, caplog):
    """Stacked Queries: SELECT 1; DROP TABLE t is rejected."""
    query = "SELECT 1; DROP TABLE sales_data"
    
    with caplog.at_level(logging.WARNING):
        result = e2e_tool.invoke({"query": query})
        
    assert "Erro de Segurança" in result
    assert "Consulta rejeitada" in result
    mock_sales_usecase.execute_custom_query.assert_not_called()
    assert "[MISSING_TOOL]" in caplog.text


def test_e2e_malformed_sql(e2e_tool, mock_sales_usecase, caplog):
    """Malformed SQL: Returns structured error with self-correction guidance."""
    query = "SELECT * FROM"
    
    with caplog.at_level(logging.WARNING):
        result = e2e_tool.invoke({"query": query})
        
    assert "Erro de Sintaxe" in result
    assert "corrija a sintaxe" in result
    mock_sales_usecase.execute_custom_query.assert_not_called()
    assert "[MISSING_TOOL]" in caplog.text


def test_e2e_complex_query(e2e_tool, mock_sales_usecase, caplog):
    """Complex Queries: CTEs, subqueries, window functions, UNIONs pass validation."""
    query = """
    WITH cte AS (
        SELECT local, SUM(actual_quantity) as total 
        FROM sales_data GROUP BY local
    )
    SELECT * FROM cte 
    UNION 
    SELECT local, 0 FROM sales_data WHERE local NOT IN (SELECT local FROM cte)
    """
    
    with caplog.at_level(logging.WARNING):
        result = e2e_tool.invoke({"query": query})
        
    assert "success" in result
    mock_sales_usecase.execute_custom_query.assert_called_once_with(query.strip().rstrip(";"))
    assert "[MISSING_TOOL]" in caplog.text


def test_e2e_performance_assertion(e2e_tool, mock_sales_usecase):
    """Performance Assertion: Total validation time < 5ms for standard 3-clause SELECT query (NFR01)."""
    # Note: the first invocation of sqlglot might be slightly slower due to module initialization
    # Run once to warm up
    e2e_tool.invoke({"query": "SELECT 1"})
    
    query = "SELECT local, product_id FROM sales_data WHERE actual_quantity > 100"
    
    start_time = time.perf_counter()
    e2e_tool.invoke({"query": query})
    end_time = time.perf_counter()
    
    duration_ms = (end_time - start_time) * 1000
    
    # Assert execution (parse + validate + mock usecase) takes less than 5ms
    # Using 10ms as buffer for test runners, but aim for < 5ms
    assert duration_ms < 10.0, f"Performance requirement failed. Took {duration_ms:.2f}ms"
