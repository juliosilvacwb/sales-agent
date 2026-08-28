"""Domain Value Objects for analytical metric results."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TopSellingProductResult:
    """Result for Top Selling Product analysis."""
    product_id: str
    total_quantity: float
    total_revenue: float
    total_records: int


@dataclass(frozen=True)
class TopLocationResult:
    """Result for Top Location by Volume analysis."""
    top_locations: List[Dict[str, Any]] = field(default_factory=list)
    primary_location: Optional[str] = None
    primary_quantity: float = 0.0


@dataclass(frozen=True)
class TotalSalesResult:
    """Result for Total Sales in a given period or overall."""
    total_quantity: float
    total_revenue: float
    total_records: int
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    average_ticket: float = 0.0


@dataclass(frozen=True)
class PlannedVsActualResult:
    """Result for Planned vs Actual quantity comparison."""
    total_planned_quantity: float
    total_actual_quantity: float
    difference_quantity: float
    achievement_percentage: float
    evaluation: str


@dataclass(frozen=True)
class PromotionImpactResult:
    """Result for analyzing promotion impacts on price and volume."""
    promoted_sales_count: int
    non_promoted_sales_count: int
    promoted_total_quantity: float
    non_promoted_total_quantity: float
    promoted_avg_actual_price: float
    non_promoted_avg_actual_price: float
    volume_lift_percentage: float
    average_discount_in_promotion: float
    summary: str


@dataclass(frozen=True)
class ServiceLevelBottleneckResult:
    """Result for analyzing service level (SLA) bottlenecks across locations."""
    worst_location: str
    worst_service_level: float
    overall_average_service_level: float
    location_averages: Dict[str, float] = field(default_factory=dict)
    summary: str = ""


@dataclass(frozen=True)
class RevenueDeficitResult:
    """Result for financial loss / revenue deficit calculation."""
    total_planned_revenue: float
    total_actual_revenue: float
    total_revenue_deficit: float
    deficit_percentage: float
    has_deficit: bool
    summary: str = ""


@dataclass(frozen=True)
class AverageDiscountResult:
    """Result for average discount margin applied."""
    overall_average_discount_percentage: float
    total_planned_revenue: float
    total_actual_revenue: float
    total_discount_value: float
    discount_by_promotion: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SeasonalityResult:
    """Result for sales seasonality analysis across months/periods."""
    monthly_volumes: Dict[str, float] = field(default_factory=dict)
    peak_month: str = ""
    peak_volume: float = 0.0
    lowest_month: str = ""
    lowest_volume: float = 0.0
    seasonality_pattern: str = ""


@dataclass(frozen=True)
class PriceElasticityResult:
    """Result for Price Elasticity of Demand analysis."""
    elasticity_coefficient: float
    percentage_change_in_price: float
    percentage_change_in_quantity: float
    demand_classification: str
    summary: str = ""
