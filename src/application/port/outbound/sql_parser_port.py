from abc import ABC, abstractmethod

from src.domain.model.sql_validation import ParsedSqlStatement
from src.domain.exception.sql_validation_exceptions import SqlSyntaxError


class SqlParserPort(ABC):
    """
    Output port interface for SQL parsing, abstracting the concrete parser library.
    
    Contract:
    - Parses SQL specifically targeting the DuckDB dialect.
    - Accurately detects whether the input contains a single or multiple statements.
    - Recursively extracts all node types and function names from the AST, 
      ignoring keywords found within string literals or aliases.
    """

    @abstractmethod
    def parse(self, raw_sql: str) -> ParsedSqlStatement:
        """
        Parses raw SQL into a domain-level ParsedSqlStatement.
        
        Args:
            raw_sql: The raw SQL string to parse.
            
        Returns:
            A ParsedSqlStatement representing the AST structure.
            
        Raises:
            SqlSyntaxError: If the SQL is malformed and cannot be parsed.
        """
        pass
