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
    "DETACH",
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
    "READ_CSV",
    "READ_TEXT",
    "READ_BLOB",
    "READ_PARQUET",
    "READ_JSON",
    "GLOB",
    "INSTALL",
    "LOAD",
    "SYSTEM",
    "WRITE_PARQUET",
    "WRITE_CSV",
]

FORBIDDEN_PATTERN = re.compile(
    r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE
)


class SQLQueryInput(BaseModel):
    """Input schema for SecuredSQLQueryTool."""
    query: str = Field(
        description=(
            "Consulta SQL analítica de leitura (apenas SELECT ou WITH) a ser executada na tabela 'sales_data' do DuckDB.\n"
            "Esquema e Regras de Domínio da tabela 'sales_data':\n"
            "- product_id (VARCHAR): Identificador do produto.\n"
            "- local (VARCHAR): Localidade / Armazém.\n"
            "- date (DATE): Data da venda.\n"
            "- planned_quantity (DOUBLE): Quantidade planejada.\n"
            "- actual_quantity (DOUBLE): Quantidade realizada.\n"
            "- planned_price (DOUBLE): Preço planejado.\n"
            "- actual_price (DOUBLE): Preço realizado.\n"
            "- service_level (DOUBLE): Nível de serviço logístico.\n"
            "- promotion_type (VARCHAR): Tipo de promoção (é NULL quando a venda não possui promoção).\n"
            "Regras Semânticas de Consulta:\n"
            "1. Vendas sem promoção: 'promotion_type' é NULL para vendas não promocionais. Para identificar produtos que NUNCA tiveram promoção, utilize `HAVING COUNT(promotion_type) = 0` ou filtro `promotion_type IS NULL`.\n"
            "2. Receita e Meta: Receita Realizada = SUM(actual_quantity * actual_price), Receita Planejada = SUM(planned_quantity * planned_price). Atingimento de meta exige `SUM(actual_quantity * actual_price) >= SUM(planned_quantity * planned_price)`."
        )
    )


class SecuredSQLQueryTool(BaseTool):
    """Secured SQL query fallback tool with strict DML/DDL protection and observability logging."""

    name: str = "secured_sql_query"
    description: str = (
        "Executa uma consulta SQL analítica de somente leitura (apenas SELECT ou WITH) diretamente na tabela 'sales_data' do DuckDB. "
        "Utilize esta ferramenta APENAS como contingência (fallback) para perguntas ad-hoc não atendidas pelas Domain Tools.\n"
        "Esquema da tabela 'sales_data': product_id, local, date, planned_quantity, actual_quantity, planned_price, actual_price, service_level, promotion_type.\n"
        "Regras Importantes:\n"
        "1. Vendas sem promoção possuem 'promotion_type' como NULL. Para consultar produtos sem promoção, utilize `HAVING COUNT(promotion_type) = 0` ou `WHERE promotion_type IS NULL`.\n"
        "2. Faturamento / Meta de Receita: Receita Realizada = SUM(actual_quantity * actual_price) vs Receita Planejada = SUM(planned_quantity * planned_price). Atingimento de meta: `SUM(actual_quantity * actual_price) >= SUM(planned_quantity * planned_price)`.\n"
        "Qualquer instrução de mutação (DROP, UPDATE, DELETE, INSERT, etc.) será categoricamente rejeitada."
    )
    args_schema: Optional[Type[BaseModel]] = SQLQueryInput  # type: ignore
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

        # 3. Security Check: No internal semicolons allowed (stacked queries protection)
        if ";" in cleaned_query:
            logger.error("Security violation: query contains internal semicolons.")
            return (
                "Erro de Segurança: Consulta rejeitada. Instruções múltiplas (encadeamento por ';') não são permitidas."
            )

        try:
            results = self.use_case.execute_custom_query(cleaned_query)
            if not results:
                logger.info("SQL Query returned 0 records: %s", cleaned_query)
                return json.dumps(
                    {
                        "status": "EMPTY_RESULT_SET",
                        "count": 0,
                        "warning": "A consulta foi executada com sucesso, mas não retornou nenhum registro.",
                        "self_correction_guidance": (
                            "Verifique se os filtros aplicados (WHERE/HAVING) não são excessivamente restritivos. "
                            "Lembre-se: 'promotion_type' é NULL para vendas não promocionais (utilize 'promotion_type IS NULL' ou 'HAVING COUNT(promotion_type) = 0'). "
                            "A receita realizada é SUM(actual_quantity * actual_price) e a meta é SUM(planned_quantity * planned_price)."
                        ),
                        "data": []
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            
            MAX_RESULTS = 50
            total_records = len(results)
            if total_records > MAX_RESULTS:
                logger.info(
                    "Truncating SQL query results from %d to %d records for latency optimization.",
                    total_records,
                    MAX_RESULTS,
                )
                truncated_results = results[:MAX_RESULTS]
                return json.dumps(
                    {
                        "total_records": total_records,
                        "returned_records": MAX_RESULTS,
                        "notice": (
                            f"A consulta retornou {total_records} registros. "
                            f"Exibindo os primeiros {MAX_RESULTS} registros para otimizar o tempo de resposta do agente. "
                            "Utilize COUNT(*) para contagens exatas no SQL se necessário."
                        ),
                        "data": truncated_results,
                    },
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

            return json.dumps(results, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error("Error executing custom SQL query '%s': %s", cleaned_query, e, exc_info=True)
            raw_err = str(e)
            sanitized_err = re.sub(r"([a-zA-Z]:[\\/][^\s:'\"]+|/[^\s:'\"]+|[A-Z]:\\[^\s:'\"]+)", "[REDACTED_PATH]", raw_err)
            return f"Erro ao executar a consulta SQL: {sanitized_err}"


def create_sql_fallback_tool(sales_use_case: SalesAnalysisUseCase) -> SecuredSQLQueryTool:
    """Factory helper to instantiate a SecuredSQLQueryTool."""
    return SecuredSQLQueryTool(use_case=sales_use_case)
