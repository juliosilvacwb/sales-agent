import pytest

from src.adapter.outbound.parser.sqlglot_parser_adapter import SqlGlotParserAdapter
from src.domain.exception.sql_validation_exceptions import SqlSyntaxError


@pytest.fixture
def parser():
    return SqlGlotParserAdapter()


def test_parse_simple_select(parser):
    result = parser.parse("SELECT * FROM t")
    assert result.root_node_type == "SELECT"
    assert result.statement_count == 1
    assert "SELECT" in result.all_node_types


def test_parse_cte(parser):
    result = parser.parse("WITH cte AS (SELECT 1) SELECT * FROM cte")
    # depending on sqlglot version, root could be SELECT (with a WITH clause)
    # usually it's SELECT, and all_node_types contains WITH, CTE, etc.
    assert result.root_node_type in ("SELECT", "WITH")
    assert result.statement_count == 1


def test_parse_drop_table(parser):
    result = parser.parse("DROP TABLE t")
    assert result.root_node_type == "DROP"
    assert "DROP" in result.all_node_types


def test_literal_isolation(parser):
    # 'DROP_TABLE' is a literal string, not a structural DROP node.
    result = parser.parse("SELECT * FROM t WHERE x = 'DROP_TABLE'")
    assert "DROP" not in result.all_node_types
    assert result.root_node_type == "SELECT"


def test_parse_function_calls(parser):
    result = parser.parse("SELECT * FROM read_csv('file.csv')")
    assert "READ_CSV" in result.all_function_names


def test_parse_stacked_queries(parser):
    result = parser.parse("SELECT 1; DROP TABLE t;")
    assert result.statement_count == 2


def test_malformed_sql(parser):
    with pytest.raises(SqlSyntaxError) as exc_info:
        parser.parse("SELECT * FROM (")
    assert exc_info.value.violation_type == "SQL_SYNTAX_ERROR"
