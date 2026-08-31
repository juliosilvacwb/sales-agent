"""Output Port (Driven Port) for Sales Data persistence and analytical aggregations."""
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from src.domain.model.aggregation_models import (
    AverageDiscountAggregation,
    LocationSalesAggregation,
    PlannedVsActualAggregation,
    PriceElasticityAggregation,
    ProductAggregation,
    PromotionImpactAggregation,
    RevenueDeficitAggregation,
    SeasonalityAggregation,
    ServiceLevelBottleneckAggregation,
    TotalSalesAggregation,
)
from src.domain.model.sale_record import SaleRecord


class SalesDataPort(ABC):
    """Abstract interface defining required data access operations for sales analytics."""

    @abstractmethod
    def aggregate_top_selling_product(self) -> Optional[ProductAggregation]:
        """Aggregates product sales and returns the top selling product."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_top_locations(self, limit: int = 5) -> Sequence[LocationSalesAggregation]:
        """Aggregates sales by location ordered by highest volume."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_total_sales(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> TotalSalesAggregation:
        """Aggregates total volume and revenue, optionally filtered by period."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_planned_vs_actual(self) -> PlannedVsActualAggregation:
        """Aggregates planned vs actual sales quantities."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_promotion_impact(self) -> PromotionImpactAggregation:
        """Aggregates sales metrics comparing promotional vs non-promotional transactions."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_service_level_bottlenecks(self) -> ServiceLevelBottleneckAggregation:
        """Aggregates average SLA across locations and fleet total."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_revenue_deficit(self) -> RevenueDeficitAggregation:
        """Aggregates planned vs actual revenues to compute potential deficits."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_average_discount(self) -> AverageDiscountAggregation:
        """Aggregates average discount percentages and breakdown by promotion."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_seasonality(self) -> SeasonalityAggregation:
        """Aggregates sales volumes by month."""
        raise NotImplementedError

    @abstractmethod
    def aggregate_price_elasticity(
        self, product_id: Optional[str] = None
    ) -> List[PriceElasticityAggregation]:
        """Aggregates promotional and baseline prices and quantities for price elasticity per product segment."""
        raise NotImplementedError

    @abstractmethod
    def get_sales_by_filter(
        self,
        product_id: Optional[str] = None,
        local: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Sequence[SaleRecord]:
        """Retrieves sales records matching specified filters."""
        raise NotImplementedError

    @abstractmethod
    def execute_read_only_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a validated read-only SQL query against the analytical engine."""
        raise NotImplementedError
