"""Secured SQL Query Tool with strict DML/DDL blocks and observability logging."""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool

from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase

logger = logging.getLogger(__name__)

# Disallowed keywords regex with word boundary check
FORBIDDEN_KEYWORDS = [
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ATTACH",
    "COPY",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "PRAGMA",
    "EXEC",
    "EXECUTE",
    "CALL",
    "GRANT",
    "REVOKE",
    "VACUUM",
    "EXPORT",
    "IMPORT",
]

FORBIDDEN_PATTERN = re.compile(
    r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE
)


class SQLQueryInput(BaseModel):
    """Input schema for SecuredSQLQueryTool."""
    query: str = Field(description="Consulta SQL analítica de leitura (apenas SELECT) a ser executada na tabela sales_data.")


class SecuredSQLQueryTool(BaseTool):
    """Secured SQL query fallback tool with strict DML/DDL protection and observability logging."""

    name: str = "secured_sql_query"
    description: str = (
        "Executa uma consulta SQL analítica de somente leitura (apenas SELECT) diretamente na tabela 'sales_data' do DuckDB. "
        "Utilize esta ferramenta APENAS como contingência (fallback) para perguntas ad-hoc não atendidas pelas Domain Tools. "
        "Qualquer instrução de mutação (DROP, UPDATE, DELETE, INSERT, etc.) será categoricamente rejeitada."
    )
    args_schema: Type[BaseModel] = SQLQueryInput
    use_case: Any = None

    def __init__(self, use_case: SalesAnalysisUseCase, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.use_case = use_case

    def _run(self, query: str) -> str:
        """Validates query security, emits [MISSING_TOOL] log, and executes on DuckDB."""
        cleaned_query = query.strip().rstrip(";")
        
        # Log observability marker with original query
        logger.warning("[MISSING_TOOL] SQL Fallback Tool triggered for query: %s", cleaned_query)

        # 1. Security Check: Forbidden Keywords
        match = FORBIDDEN_PATTERN.search(cleaned_query)
        if match:
            forbidden_word = match.group(0).upper()
            logger.error("Security violation: query contains forbidden keyword '%s'", forbidden_word)
            return (
                f"Erro de Segurança: A instrução '{forbidden_word}' é proibida. "
                "Apenas consultas analíticas de leitura (SELECT) são permitidas."
            )

        # 2. Security Check: Must start with SELECT or WITH
        first_word = cleaned_query.split()[0].upper() if cleaned_query.split() else ""
        if first_word not in ("SELECT", "WITH", "DESCRIBE", "EXPLAIN"):
            logger.error("Security violation: query does not start with SELECT/WITH. Found: '%s'", first_word)
            return (
                f"Erro de Segurança: Consulta rejeitada. Apenas instruções de leitura iniciando em SELECT ou WITH são permitidas."
            )

        try:
            results = self.use_case.execute_custom_query(cleaned_query)
            if not results:
                return "A consulta foi executada com sucesso, mas não retornou nenhum registro."
            return json.dumps(results, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Error executing custom SQL query '%s': %s", cleaned_query, e, exc_info=True)
            return f"Erro ao executar a consulta SQL: {str(e)}"


def create_sql_fallback_tool(sales_use_case: SalesAnalysisUseCase) -> SecuredSQLQueryTool:
    """Factory helper to instantiate a SecuredSQLQueryTool."""
    return SecuredSQLQueryTool(use_case=sales_use_case)
