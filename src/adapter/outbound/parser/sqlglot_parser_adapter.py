import re
from typing import Set

import sqlglot
from sqlglot import exp

from src.application.port.outbound.sql_parser_port import SqlParserPort
from src.domain.exception.sql_validation_exceptions import SqlSyntaxError
from src.domain.model.sql_validation import ParsedSqlStatement


class SqlGlotParserAdapter(SqlParserPort):
    """Adapter implementing SqlParserPort using the sqlglot library."""

    def parse(self, raw_sql: str) -> ParsedSqlStatement:
        try:
            parsed_statements = sqlglot.parse(raw_sql, dialect="duckdb")
        except sqlglot.errors.ParseError as e:
            # Sanitize the error message to avoid exposing raw stack traces
            error_details = str(e).split("\n")[0]
            raise SqlSyntaxError(
                violation_type="SQL_SYNTAX_ERROR",
                detail=f"Failed to parse SQL: {error_details}",
            ) from e

        # sqlglot.parse can return None for empty strings or a list with None elements
        if not parsed_statements or all(stmt is None for stmt in parsed_statements):
            raise SqlSyntaxError(
                violation_type="SQL_SYNTAX_ERROR",
                detail="Empty or invalid SQL statement.",
            )

        statement_count = len([s for s in parsed_statements if s is not None])
        ast_root = parsed_statements[0]

        if ast_root is None:
            raise SqlSyntaxError(
                violation_type="SQL_SYNTAX_ERROR",
                detail="Failed to extract AST root from SQL.",
            )

        root_node_type = type(ast_root).__name__.upper()

        all_node_types: Set[str] = set()
        all_function_names: Set[str] = set()

        for node in ast_root.walk():
            # Add node type
            all_node_types.add(type(node).__name__.upper())

            # Detect function calls
            if isinstance(node, exp.Func) or type(node).__name__.upper() == "ANONYMOUS":
                names = []
                if hasattr(node, "name") and node.name:
                    names.append(node.name)
                if hasattr(node, "sql_name"):
                    names.append(node.sql_name())
                class_name = type(node).__name__
                names.append(class_name)
                # Convert CamelCase like ReadCSV -> READ_CSV
                snake = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name)
                names.append(snake)

                for n in names:
                    if n:
                        all_function_names.add(n.upper())

        return ParsedSqlStatement(
            root_node_type=root_node_type,
            all_node_types=frozenset(all_node_types),
            all_function_names=frozenset(all_function_names),
            statement_count=statement_count,
            raw_sql=raw_sql,
        )
