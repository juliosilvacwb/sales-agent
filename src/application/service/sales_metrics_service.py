"""Application Service implementing SalesAnalysisUseCase."""
import logging
from datetime import date
from typing import Any, Dict, List, Optional, Union

from src.application.port.inbound.sales_analysis_usecase import SalesAnalysisUseCase
from src.application.port.outbound.sales_data_port import SalesDataPort
from src.domain.model.metric_result import (
    AverageDiscountResult,
    CatalogPriceElasticityOverview,
    PlannedVsActualResult,
    PriceElasticityResult,
    PromotionImpactResult,
    RevenueDeficitResult,
    SeasonalityResult,
    ServiceLevelBottleneckResult,
    TopLocationResult,
    TopSellingProductResult,
    TotalSalesResult,
)
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService

logger = logging.getLogger(__name__)


class SalesMetricsApplicationService(SalesAnalysisUseCase):
    """Orchestrates sales data retrieval via Output Port and executes domain metric calculations."""

    def __init__(
        self,
        sales_data_port: SalesDataPort,
        basic_metrics_service: Optional[BasicMetricsService] = None,
        advanced_metrics_service: Optional[AdvancedMetricsService] = None,
    ) -> None:
        self._sales_data_port = sales_data_port
        self._basic_metrics = basic_metrics_service or BasicMetricsService()
        self._advanced_metrics = advanced_metrics_service or AdvancedMetricsService()

    def get_top_selling_product(self) -> TopSellingProductResult:
        """Identifies the product with the highest total sales volume."""
        logger.info("Executing use case: get_top_selling_product via SQL aggregation pushdown")
        agg = self._sales_data_port.aggregate_top_selling_product()
        return self._basic_metrics.get_top_selling_product(agg)

    def get_top_locations_by_volume(self, limit: int = 5) -> TopLocationResult:
        """Identifies locations sorted by highest sales volume."""
        logger.info("Executing use case: get_top_locations_by_volume (limit=%d)", limit)
        aggs = self._sales_data_port.aggregate_top_locations(limit=limit)
        return self._basic_metrics.get_top_locations_by_volume(aggs, limit=limit)

    def get_total_sales_in_period(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> TotalSalesResult:
        """Calculates total sales volume, revenue and average ticket in a period."""
        logger.info(
            "Executing use case: get_total_sales_in_period (start=%s, end=%s)",
            start_date,
            end_date,
        )
        agg = self._sales_data_port.aggregate_total_sales(start_date=start_date, end_date=end_date)
        return self._basic_metrics.get_total_sales_in_period(
            agg, start_date=start_date, end_date=end_date
        )

    def compare_planned_vs_actual_quantity(self) -> PlannedVsActualResult:
        """Compares budgeted planned quantities against actual realized quantities."""
        logger.info("Executing use case: compare_planned_vs_actual_quantity")
        agg = self._sales_data_port.aggregate_planned_vs_actual()
        return self._basic_metrics.compare_planned_vs_actual_quantity(agg)

    def analyze_promotion_impact(self) -> PromotionImpactResult:
        """Analyzes promotional lift, discounts, and volume impact."""
        logger.info("Executing use case: analyze_promotion_impact")
        agg = self._sales_data_port.aggregate_promotion_impact()
        return self._basic_metrics.analyze_promotion_impact(agg)

    def analyze_service_level_bottlenecks(self) -> ServiceLevelBottleneckResult:
        """Identifies logistics service level (SLA) bottlenecks across locations."""
        logger.info("Executing use case: analyze_service_level_bottlenecks")
        agg = self._sales_data_port.aggregate_service_level_bottlenecks()
        return self._advanced_metrics.analyze_service_level_bottlenecks(agg)

    def calculate_revenue_deficit(self) -> RevenueDeficitResult:
        """Calculates estimated financial loss/deficit due to planned vs actual variance."""
        logger.info("Executing use case: calculate_revenue_deficit")
        agg = self._sales_data_port.aggregate_revenue_deficit()
        return self._advanced_metrics.calculate_revenue_deficit(agg)

    def calculate_average_discount(self) -> AverageDiscountResult:
        """Calculates average discount margin applied against planned prices."""
        logger.info("Executing use case: calculate_average_discount")
        agg = self._sales_data_port.aggregate_average_discount()
        return self._advanced_metrics.calculate_average_discount(agg)

    def identify_sales_seasonality(self) -> SeasonalityResult:
        """Identifies monthly peaks, valleys, and temporal sales patterns."""
        logger.info("Executing use case: identify_sales_seasonality")
        agg = self._sales_data_port.aggregate_seasonality()
        return self._advanced_metrics.identify_sales_seasonality(agg)

    def calculate_price_elasticity(
        self, product_id: Optional[str] = None
    ) -> Union[PriceElasticityResult, CatalogPriceElasticityOverview]:
        """Calculates price elasticity of demand for a specific product or the whole catalog."""
        logger.info("Executing use case: calculate_price_elasticity (product_id=%s)", product_id)
        agg = self._sales_data_port.aggregate_price_elasticity(product_id=product_id)
        return self._advanced_metrics.calculate_price_elasticity(agg, target_product_id=product_id)

    def execute_custom_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a secured ad-hoc SQL query for fallback analytical requests."""
        logger.info("Executing use case: execute_custom_query")
        return self._sales_data_port.execute_read_only_query(query)
