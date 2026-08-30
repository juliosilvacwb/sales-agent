from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SqlViolationType(Enum):
    """Enumeration classifying all possible SQL security violation types."""
    
    DISALLOWED_ROOT_OPERATION = "The root operation is not allowed (e.g., must be SELECT, WITH, or UNION)."
    FORBIDDEN_MUTATIONAL_NODE = "A forbidden mutational node was found in the syntax tree."
    FORBIDDEN_FUNCTION_CALL = "A forbidden function call was detected in the syntax tree."
    STACKED_QUERIES_DETECTED = "Multiple stacked SQL queries were detected."
    SQL_SYNTAX_ERROR = "The SQL statement contains a syntax error and could not be parsed."

    @property
    def description(self) -> str:
        return self.value


@dataclass(frozen=True)
class SqlValidationResult:
    """Immutable value object representing the outcome of SQL security validation."""
    
    is_valid: bool
    violation_type: Optional[SqlViolationType] = None
    violation_detail: Optional[str] = None
    offending_node: Optional[str] = None

    @classmethod
    def success(cls) -> "SqlValidationResult":
        return cls(is_valid=True)

    @classmethod
    def violation(
        cls, 
        violation_type: SqlViolationType, 
        detail: str, 
        node: Optional[str] = None
    ) -> "SqlValidationResult":
        return cls(
            is_valid=False, 
            violation_type=violation_type, 
            violation_detail=detail, 
            offending_node=node
        )


@dataclass(frozen=True)
class ParsedSqlStatement:
    """Domain-level abstraction representing a parsed SQL statement."""
    
    root_node_type: str
    all_node_types: frozenset[str]
    all_function_names: frozenset[str]
    statement_count: int
    raw_sql: str
