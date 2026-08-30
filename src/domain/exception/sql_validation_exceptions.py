"""Domain-specific exceptions for SQL Validation."""
from typing import Optional


class SqlValidationError(Exception):
    """Base domain exception for SQL validation failures."""
    
    def __init__(self, violation_type: str, detail: str) -> None:
        self.violation_type = violation_type
        self.detail = detail
        super().__init__(f"SQL Validation Error [{violation_type}]: {detail}")


class SqlSyntaxError(SqlValidationError):
    """Raised when the SQL statement contains syntax errors and cannot be parsed."""
    pass


class SqlSecurityViolationError(SqlValidationError):
    """Raised when the SQL statement contains forbidden operations."""
    
    def __init__(self, violation_type: str, detail: str, offending_node_type: Optional[str] = None) -> None:
        self.offending_node_type = offending_node_type
        super().__init__(violation_type=violation_type, detail=detail)
