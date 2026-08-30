import pytest

from src.domain.model.sql_validation import ParsedSqlStatement, SqlViolationType
from src.domain.service.sql_security_validator import SqlSecurityValidator


@pytest.fixture
def validator():
    return SqlSecurityValidator()


def create_statement(
    root_node_type="SELECT",
    all_node_types=None,
    all_function_names=None,
    statement_count=1,
    raw_sql="SELECT * FROM table"
) -> ParsedSqlStatement:
    if all_node_types is None:
        all_node_types = frozenset({"SELECT", "IDENTIFIER"})
    if all_function_names is None:
        all_function_names = frozenset()
        
    return ParsedSqlStatement(
        root_node_type=root_node_type,
        all_node_types=frozenset(all_node_types),
        all_function_names=frozenset(all_function_names),
        statement_count=statement_count,
        raw_sql=raw_sql
    )


@pytest.mark.parametrize("root_type", ["SELECT", "WITH", "UNION"])
def test_valid_root_operations(validator, root_type):
    statement = create_statement(root_node_type=root_type)
    result = validator.validate(statement)
    assert result.is_valid is True
    assert result.violation_type is None


@pytest.mark.parametrize("root_type", ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"])
def test_forbidden_root_operations(validator, root_type):
    statement = create_statement(root_node_type=root_type)
    result = validator.validate(statement)
    assert result.is_valid is False
    assert result.violation_type == SqlViolationType.DISALLOWED_ROOT_OPERATION
    assert result.violation_detail == f"Root operation '{root_type}' is not allowed."


@pytest.mark.parametrize(
    "mutational_node",
    [
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", 
        "REPLACE", "TRUNCATE", "PRAGMA", "ATTACH", "DETACH", "COPY", 
        "LOAD", "INSTALL", "COMMAND"
    ]
)
def test_forbidden_mutational_nodes(validator, mutational_node):
    statement = create_statement(
        root_node_type="SELECT",
        all_node_types={"SELECT", "IDENTIFIER", mutational_node}
    )
    result = validator.validate(statement)
    assert result.is_valid is False
    assert result.violation_type == SqlViolationType.FORBIDDEN_MUTATIONAL_NODE
    assert result.offending_node == mutational_node


@pytest.mark.parametrize(
    "forbidden_function",
    [
        "READ_CSV", "READ_TEXT", "READ_BLOB", "READ_PARQUET", "READ_JSON", 
        "GLOB", "READ_CSV_AUTO", "WRITE_CSV", "WRITE_PARQUET", "EXPORT_PARQUET"
    ]
)
def test_forbidden_function_calls(validator, forbidden_function):
    statement = create_statement(
        root_node_type="SELECT",
        all_function_names={forbidden_function, "SUM"}
    )
    result = validator.validate(statement)
    assert result.is_valid is False
    assert result.violation_type == SqlViolationType.FORBIDDEN_FUNCTION_CALL
    assert result.offending_node == forbidden_function


def test_stacked_queries_detected(validator):
    statement = create_statement(statement_count=2, raw_sql="SELECT 1; DROP TABLE users;")
    result = validator.validate(statement)
    assert result.is_valid is False
    assert result.violation_type == SqlViolationType.STACKED_QUERIES_DETECTED
    assert "Expected 1 statement" in result.violation_detail


def test_string_literal_safety(validator):
    # Represents: SELECT * FROM t WHERE col = 'DROP_TABLE'
    # The adapter should parse 'DROP_TABLE' as a literal, NOT a drop node.
    # Therefore, all_node_types does not contain "DROP".
    statement = create_statement(
        root_node_type="SELECT",
        all_node_types={"SELECT", "WHERE", "LITERAL", "IDENTIFIER"},
        raw_sql="SELECT * FROM t WHERE col = 'DROP_TABLE'"
    )
    result = validator.validate(statement)
    assert result.is_valid is True
