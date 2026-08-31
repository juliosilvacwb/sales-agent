"""Secured SQL Query Tool with strict DML/DDL blocks and observability logging."""
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool, ToolException

from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase
from src.application.port.outbound.sql_parser_port import SqlParserPort
from src.domain.service.sql_security_validator import SqlSecurityValidator
from src.domain.exception.sql_validation_exceptions import SqlSyntaxError
from src.adapter.outbound.parser.sqlglot_parser_adapter import SqlGlotParserAdapter

logger = logging.getLogger(__name__)


def _sanitize_path_details(raw_error: str) -> str:
    """Sanitizes error messages by replacing host file paths and directories with [REDACTED_PATH]."""
    return re.sub(
        r"([a-zA-Z]:[\\/][^\s:'\"]+|/[^\s:'\"]+|[A-Z]:\\[^\s:'\"]+|\\\\[^\s:'\"]+)",
        "[REDACTED_PATH]",
        raw_error,
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
    handle_tool_error: Optional[Union[bool, str, Callable[[ToolException], Any]]] = True
    use_case: Optional[SalesAnalysisUseCase] = None
    sql_parser_port: Optional[SqlParserPort] = None
    validator: Optional[SqlSecurityValidator] = None

    def __init__(
        self, 
        use_case: SalesAnalysisUseCase, 
        sql_parser_port: SqlParserPort,
        validator: SqlSecurityValidator,
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.use_case = use_case
        self.sql_parser_port = sql_parser_port
        self.validator = validator

    def _run(self, query: str) -> str:
        """Validates query security, emits [MISSING_TOOL] log, and executes on DuckDB."""
        if query is None or not isinstance(query, str) or not query.strip():
            raise ToolException("Consulta SQL inválida ou vazia.")

        if self.sql_parser_port is None:
            raise ToolException("SqlParserPort não configurado.")
        if self.validator is None:
            raise ToolException("SqlSecurityValidator não configurado.")
        if self.use_case is None:
            raise ToolException("SalesAnalysisUseCase não configurado.")

        cleaned_query = query.strip().rstrip(";")
        
        # Log observability marker with original query
        logger.warning("[MISSING_TOOL] SQL Fallback Tool triggered for query: %s", cleaned_query)

        try:
            parsed_statement = self.sql_parser_port.parse(cleaned_query)
        except SqlSyntaxError as e:
            logger.error("SQL Syntax Error: %s", e)
            raise ToolException(
                f"Erro de Sintaxe: Não foi possível analisar a consulta SQL. "
                f"Detalhe: {e.detail}. Por favor, corrija a sintaxe e tente novamente."
            )
        except Exception as e:
            logger.error("Unexpected error during parsing: %s", e)
            sanitized_err = _sanitize_path_details(str(e))
            raise ToolException(f"Erro ao executar a consulta SQL: {sanitized_err}")

        validation_result = self.validator.validate(parsed_statement)
        if not validation_result.is_valid:
            logger.error("Security violation: %s - %s", validation_result.violation_type, validation_result.violation_detail)
            
            # Match existing error format (PT-BR)
            offending_info = ""
            if validation_result.offending_node:
                offending_info = f"'{validation_result.offending_node}'"
            elif validation_result.violation_type and validation_result.violation_type.name == "DISALLOWED_ROOT_OPERATION":
                offending_info = f"'{parsed_statement.root_node_type}'"
                
            if offending_info:
                raise ToolException(
                    f"Erro de Segurança: A instrução {offending_info} é proibida. "
                    "Apenas consultas analíticas de leitura (SELECT/WITH) são permitidas."
                )
            raise ToolException(
                f"Erro de Segurança: Consulta rejeitada. "
                f"Detalhe: {validation_result.violation_detail} "
                "Apenas consultas analíticas de leitura (SELECT/WITH) são permitidas."
            )

        try:
            raw_results = self.use_case.execute_custom_query(cleaned_query)
            if raw_results is None:
                results: List[Dict[str, Any]] = []
            elif isinstance(raw_results, list):
                results = raw_results
            else:
                results = list(raw_results)

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
            sanitized_err = _sanitize_path_details(str(e))
            raise ToolException(f"Erro ao executar a consulta SQL: {sanitized_err}")


def create_sql_fallback_tool(
    sales_use_case: SalesAnalysisUseCase,
    sql_parser_port: Optional[SqlParserPort] = None,
    validator: Optional[SqlSecurityValidator] = None
) -> SecuredSQLQueryTool:
    """Factory helper to instantiate a SecuredSQLQueryTool."""
    if sales_use_case is None:
        raise ValueError("sales_use_case must not be None")
    if sql_parser_port is None:
        sql_parser_port = SqlGlotParserAdapter()
    if validator is None:
        validator = SqlSecurityValidator()
        
    return SecuredSQLQueryTool(
        use_case=sales_use_case,
        sql_parser_port=sql_parser_port,
        validator=validator
    )
