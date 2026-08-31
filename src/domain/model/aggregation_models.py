"""Domain Value Objects for aggregated sales metrics data structures."""
from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class ProductAggregation:
    """Aggregated metrics for top selling product."""
    product_id: str
    total_quantity: float
    total_revenue: float
    total_records: int


@dataclass(frozen=True)
class LocationSalesAggregation:
    """Aggregated sales metrics for a single location."""
    local: str
    total_quantity: float
    total_revenue: float


@dataclass(frozen=True)
class TotalSalesAggregation:
    """Aggregated sales volume and revenue totals."""
    total_quantity: float
    total_revenue: float
    total_records: int


@dataclass(frozen=True)
class PlannedVsActualAggregation:
    """Aggregated planned vs actual quantities."""
    total_planned_quantity: float
    total_actual_quantity: float
    total_records: int


@dataclass(frozen=True)
class PromotionImpactAggregation:
    """Aggregated metrics comparing promoted vs non-promoted sales."""
    promoted_sales_count: int
    non_promoted_sales_count: int
    promoted_total_quantity: float
    non_promoted_total_quantity: float
    promoted_avg_actual_price: float
    non_promoted_avg_actual_price: float
    average_discount_in_promotion: float
    total_records: int


@dataclass(frozen=True)
class ServiceLevelBottleneckAggregation:
    """Aggregated SLA metrics across locations."""
    location_averages: Dict[str, float] = field(default_factory=dict)
    overall_average_service_level: float = 0.0
    total_records: int = 0


@dataclass(frozen=True)
class RevenueDeficitAggregation:
    """Aggregated planned vs actual revenues."""
    total_planned_revenue: float
    total_actual_revenue: float
    total_records: int


@dataclass(frozen=True)
class AverageDiscountAggregation:
    """Aggregated discount metrics and breakdown by promotion."""
    total_planned_revenue: float
    total_actual_revenue: float
    total_discount_value: float
    overall_average_discount_percentage: float
    discount_by_promotion: Dict[str, float] = field(default_factory=dict)
    total_records: int = 0


@dataclass(frozen=True)
class SeasonalityAggregation:
    """Aggregated monthly sales volume totals."""
    monthly_volumes: Dict[str, float] = field(default_factory=dict)
    total_records: int = 0


@dataclass(frozen=True)
class PriceElasticityAggregation:
    """Aggregated metrics for price elasticity of demand calculation."""
    promoted_avg_price: float
    non_promoted_avg_price: float
    promoted_avg_qty: float
    non_promoted_avg_qty: float
    promoted_count: int
    non_promoted_count: int
    total_records: int = 0
    product_id: str = ""

