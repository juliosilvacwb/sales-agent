import sqlglot
from sqlglot import exp

from src.application.port.outbound.sql_parser_port import SqlParserPort
from src.domain.model.sql_validation import ParsedSqlStatement
from src.domain.exception.sql_validation_exceptions import SqlSyntaxError


class SqlGlotParserAdapter(SqlParserPort):
    """
    Adapter implementing SqlParserPort using the sqlglot library.
    """

    def parse(self, raw_sql: str) -> ParsedSqlStatement:
        try:
            parsed_statements = sqlglot.parse(raw_sql, dialect="duckdb")
        except sqlglot.errors.ParseError as e:
            # Sanitize the error message to avoid exposing raw stack traces
            error_details = str(e).split("\n")[0]
            raise SqlSyntaxError(
                violation_type="SQL_SYNTAX_ERROR",
                detail=f"Failed to parse SQL: {error_details}"
            ) from e

        # sqlglot.parse can return None for empty strings or a list with None elements
        if not parsed_statements or all(stmt is None for stmt in parsed_statements):
            raise SqlSyntaxError(
                violation_type="SQL_SYNTAX_ERROR",
                detail="Empty or invalid SQL statement."
            )

        statement_count = len([s for s in parsed_statements if s is not None])
        ast_root = parsed_statements[0]
        
        if ast_root is None:
            raise SqlSyntaxError(
                violation_type="SQL_SYNTAX_ERROR",
                detail="Failed to extract AST root from SQL."
            )

        root_node_type = type(ast_root).__name__.upper()
        
        all_node_types = set()
        all_function_names = set()

        for node, parent, key in ast_root.walk():
            # Add node type
            all_node_types.add(type(node).__name__.upper())
            
            # Detect function calls
            if isinstance(node, exp.Func):
                if hasattr(node, "name"):
                    all_function_names.add(node.name.upper())
            elif type(node).__name__.upper() == "ANONYMOUS":
                if hasattr(node, "name"):
                    all_function_names.add(node.name.upper())

        return ParsedSqlStatement(
            root_node_type=root_node_type,
            all_node_types=frozenset(all_node_types),
            all_function_names=frozenset(all_function_names),
            statement_count=statement_count,
            raw_sql=raw_sql
        )
