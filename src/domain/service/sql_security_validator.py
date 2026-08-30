from src.domain.model.sql_validation import (
    ParsedSqlStatement,
    SqlValidationResult,
    SqlViolationType,
)


class SqlSecurityValidator:
    """Pure domain service for SQL security validation rules."""

    ALLOWED_ROOT_OPERATIONS = frozenset({"SELECT", "WITH", "UNION"})

    FORBIDDEN_MUTATIONAL_NODES = frozenset({
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", 
        "REPLACE", "TRUNCATE", "PRAGMA", "ATTACH", "DETACH", "COPY", 
        "LOAD", "INSTALL", "COMMAND"
    })

    FORBIDDEN_FUNCTIONS = frozenset({
        "READ_CSV", "READ_TEXT", "READ_BLOB", "READ_PARQUET", "READ_JSON", 
        "GLOB", "READ_CSV_AUTO", "WRITE_CSV", "WRITE_PARQUET", "EXPORT_PARQUET"
    })

    def validate(self, statement: ParsedSqlStatement) -> SqlValidationResult:
        """
        Evaluates a ParsedSqlStatement against deterministic structural security rules.
        """
        # Rule 2: Stacked Queries (Evaluate early to fail fast on multiple queries)
        if statement.statement_count != 1:
            return SqlValidationResult.violation(
                violation_type=SqlViolationType.STACKED_QUERIES_DETECTED,
                detail=f"Expected 1 statement, but found {statement.statement_count} statements."
            )

        # Rule 1: Root Operation
        if statement.root_node_type not in self.ALLOWED_ROOT_OPERATIONS:
            return SqlValidationResult.violation(
                violation_type=SqlViolationType.DISALLOWED_ROOT_OPERATION,
                detail=f"Root operation '{statement.root_node_type}' is not allowed."
            )

        # Rule 3: Forbidden Mutational Nodes
        mutational_intersection = statement.all_node_types.intersection(self.FORBIDDEN_MUTATIONAL_NODES)
        if mutational_intersection:
            offending_node = sorted(list(mutational_intersection))[0]
            return SqlValidationResult.violation(
                violation_type=SqlViolationType.FORBIDDEN_MUTATIONAL_NODE,
                detail=f"Forbidden operation '{offending_node}' detected in the syntax tree.",
                node=offending_node
            )

        # Rule 4: Forbidden Functions
        function_intersection = statement.all_function_names.intersection(self.FORBIDDEN_FUNCTIONS)
        if function_intersection:
            offending_function = sorted(list(function_intersection))[0]
            return SqlValidationResult.violation(
                violation_type=SqlViolationType.FORBIDDEN_FUNCTION_CALL,
                detail=f"Forbidden function '{offending_function}' detected in the syntax tree.",
                node=offending_function
            )

        # All rules pass
        return SqlValidationResult.success()
