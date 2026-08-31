"""LangChain Domain Tools wrapping SalesAnalysisUseCase."""
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import List, Optional

from langchain_core.tools import BaseTool, ToolException, tool

from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase

logger = logging.getLogger(__name__)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parses date string supporting Brazilian format (DD/MM/YYYY) and ISO format (YYYY-MM-DD)."""
    if not date_str or not date_str.strip():
        return None
    cleaned = date_str.strip()

    # Try Brazilian formats first: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, DD/MM/YY
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass

    # Try ISO format: YYYY-MM-DD
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        pass

    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass

    raise ValueError(
        f"Formato de data inválido: '{date_str}'. Formatos aceitos: DD/MM/YYYY ou YYYY-MM-DD."
    )


def _to_json_str(obj: object) -> str:
    """Helper to convert dataclass or dict to JSON string formatted for LLM consumption."""
    if is_dataclass(obj) and not isinstance(obj, type):
        data = asdict(obj)
    elif isinstance(obj, dict):
        data = obj
    else:
        return str(obj)
    return json.dumps(data, indent=2, ensure_ascii=False)


def create_domain_tools(sales_use_case: SalesAnalysisUseCase) -> List[BaseTool]:
    """Factory creating the 10 LangChain Domain Tools bound to a SalesAnalysisUseCase instance."""

    @tool
    def get_top_selling_product() -> str:
        """Identifica o produto mais vendido por volume total de vendas e receita gerada."""
        logger.info("Tool invoked: get_top_selling_product")
        result = sales_use_case.get_top_selling_product()
        return _to_json_str(result)

    @tool
    def get_top_locations_by_volume(limit: int = 5) -> str:
        """Identifica as localidades com maior volume de vendas em ordem decrescente.
        
        Args:
            limit: Quantidade de localidades a retornar (padrão: 5, mínimo: 1, máximo: 100).
        """
        try:
            safe_limit = max(1, min(int(limit), 100))
        except (ValueError, TypeError):
            safe_limit = 5
        logger.info("Tool invoked: get_top_locations_by_volume with limit=%s (safe_limit=%d)", limit, safe_limit)
        result = sales_use_case.get_top_locations_by_volume(limit=safe_limit)
        return _to_json_str(result)

    @tool
    def get_total_sales_in_period(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """Calcula o total de vendas (volume, faturamento e ticket médio) em um período ou geral.
        
        Args:
            start_date: Data inicial no formato brasileiro DD/MM/YYYY ou ISO YYYY-MM-DD (opcional).
            end_date: Data final no formato brasileiro DD/MM/YYYY ou ISO YYYY-MM-DD (opcional).
        """
        logger.info("Tool invoked: get_total_sales_in_period (start=%s, end=%s)", start_date, end_date)
        try:
            parsed_start = _parse_date(start_date)
            parsed_end = _parse_date(end_date)
        except ValueError as e:
            raise ToolException(f"Erro de validação de data: {str(e)}")

        result = sales_use_case.get_total_sales_in_period(
            start_date=parsed_start, end_date=parsed_end
        )
        return _to_json_str(result)

    @tool
    def compare_planned_vs_actual_quantity() -> str:
        """Compara a quantidade total planejada (orçada) versus a quantidade realizada e percentual de meta."""
        logger.info("Tool invoked: compare_planned_vs_actual_quantity")
        result = sales_use_case.compare_planned_vs_actual_quantity()
        return _to_json_str(result)

    @tool
    def analyze_promotion_impact() -> str:
        """Analisa o impacto das promoções comparando preços, volume com/sem promoção e lift gerado."""
        logger.info("Tool invoked: analyze_promotion_impact")
        result = sales_use_case.analyze_promotion_impact()
        return _to_json_str(result)

    @tool
    def analyze_service_level_bottlenecks() -> str:
        """Identifica qual localidade apresenta o pior SLA logístico (nível de serviço) médio e gargalos."""
        logger.info("Tool invoked: analyze_service_level_bottlenecks")
        result = sales_use_case.analyze_service_level_bottlenecks()
        return _to_json_str(result)

    @tool
    def calculate_revenue_deficit() -> str:
        """Calcula a perda financeira estimada (déficit de receita) devido a desvios entre planejado e realizado."""
        logger.info("Tool invoked: calculate_revenue_deficit")
        result = sales_use_case.calculate_revenue_deficit()
        return _to_json_str(result)

    @tool
    def calculate_average_discount() -> str:
        """Calcula a margem de desconto médio aplicado frente aos preços planejados e valor total de desconto."""
        logger.info("Tool invoked: calculate_average_discount")
        result = sales_use_case.calculate_average_discount()
        return _to_json_str(result)

    @tool
    def identify_sales_seasonality() -> str:
        """Identifica padrões temporais de sazonalidade mensal de vendas, mês de pico e mês mais fraco."""
        logger.info("Tool invoked: identify_sales_seasonality")
        result = sales_use_case.identify_sales_seasonality()
        return _to_json_str(result)

    @tool
    def calculate_price_elasticity(product_id: Optional[str] = None) -> str:
        """Calcula o coeficiente de elasticidade-preço da demanda para um produto específico ou visão geral do catálogo.
        
        Args:
            product_id: Identificador do produto (ex: 'PROD_01'). Se omitido (None), calcula e ranqueia a elasticidade de todo o catálogo.
        """
        logger.info("Tool invoked: calculate_price_elasticity (product_id=%s)", product_id)
        result = sales_use_case.calculate_price_elasticity(product_id=product_id)
        return _to_json_str(result)

    tools = [
        get_top_selling_product,
        get_top_locations_by_volume,
        get_total_sales_in_period,
        compare_planned_vs_actual_quantity,
        analyze_promotion_impact,
        analyze_service_level_bottlenecks,
        calculate_revenue_deficit,
        calculate_average_discount,
        identify_sales_seasonality,
        calculate_price_elasticity,
    ]
    for t in tools:
        t.handle_tool_error = True
    return tools
