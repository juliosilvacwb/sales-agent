"""Input Port (Driving Port) defining Use Cases for sales data analysis."""
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional, Union

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


class SalesAnalysisUseCase(ABC):
    """Driving Port interface exposing business capabilities for sales analysis."""

    @abstractmethod
    def get_top_selling_product(self) -> TopSellingProductResult:
        """Identifies the product with the highest total sales volume."""
        raise NotImplementedError

    @abstractmethod
    def get_top_locations_by_volume(self, limit: int = 5) -> TopLocationResult:
        """Identifies locations sorted by highest sales volume."""
        raise NotImplementedError

    @abstractmethod
    def get_total_sales_in_period(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> TotalSalesResult:
        """Calculates total sales volume, revenue and average ticket in a period."""
        raise NotImplementedError

    @abstractmethod
    def compare_planned_vs_actual_quantity(self) -> PlannedVsActualResult:
        """Compares budgeted planned quantities against actual realized quantities."""
        raise NotImplementedError

    @abstractmethod
    def analyze_promotion_impact(self) -> PromotionImpactResult:
        """Analyzes promotional lift, discounts, and volume impact."""
        raise NotImplementedError

    @abstractmethod
    def analyze_service_level_bottlenecks(self) -> ServiceLevelBottleneckResult:
        """Identifies logistics service level (SLA) bottlenecks across locations."""
        raise NotImplementedError

    @abstractmethod
    def calculate_revenue_deficit(self) -> RevenueDeficitResult:
        """Calculates estimated financial loss/deficit due to planned vs actual variance."""
        raise NotImplementedError

    @abstractmethod
    def calculate_average_discount(self) -> AverageDiscountResult:
        """Calculates average discount margin applied against planned prices."""
        raise NotImplementedError

    @abstractmethod
    def identify_sales_seasonality(self) -> SeasonalityResult:
        """Identifies monthly peaks, valleys, and temporal sales patterns."""
        raise NotImplementedError

    @abstractmethod
    def calculate_price_elasticity(
        self, product_id: Optional[str] = None
    ) -> Union[PriceElasticityResult, CatalogPriceElasticityOverview]:
        """Calculates price elasticity of demand for a specific product or the whole catalog."""
        raise NotImplementedError

    @abstractmethod
    def execute_custom_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a secured ad-hoc SQL query for non-standard queries."""
        raise NotImplementedError
