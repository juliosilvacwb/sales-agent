"""Unit tests for AdvancedMetricsService using aggregated data structures."""
import pytest

from src.domain.model.aggregation_models import (
    AverageDiscountAggregation,
    PriceElasticityAggregation,
    RevenueDeficitAggregation,
    SeasonalityAggregation,
    ServiceLevelBottleneckAggregation,
)
from src.domain.service.advanced_metrics_service import AdvancedMetricsService


def test_analyze_service_level_bottlenecks():
    service = AdvancedMetricsService()
    agg = ServiceLevelBottleneckAggregation(
        location_averages={"Whse_A": 0.985, "Whse_B": 0.825},
        overall_average_service_level=0.905,
        total_records=4,
    )
    result = service.analyze_service_level_bottlenecks(agg)

    assert result.worst_location == "Whse_B"
    assert round(result.worst_service_level, 3) == 0.825
    assert "Whse_B" in result.summary


def test_analyze_service_level_bottlenecks_equal_sla():
    service = AdvancedMetricsService()
    agg = ServiceLevelBottleneckAggregation(
        location_averages={"Whse_A": 0.98, "Whse_B": 0.98, "Whse_C": 0.98},
        overall_average_service_level=0.98,
        total_records=3,
    )
    result = service.analyze_service_level_bottlenecks(agg)

    assert result.worst_location == "N/A"
    assert result.worst_service_level == 0.98
    assert result.overall_average_service_level == 0.98
    assert "No logistics SLA bottleneck identified" in result.summary


def test_analyze_service_level_bottlenecks_empty():
    service = AdvancedMetricsService()
    result = service.analyze_service_level_bottlenecks(None)
    assert result.worst_location == "N/A"
    assert result.worst_service_level == 0.0
    assert result.summary == "No records to analyze for SLA bottlenecks"


def test_calculate_revenue_deficit():
    service = AdvancedMetricsService()
    agg = RevenueDeficitAggregation(
        total_planned_revenue=70000.0,
        total_actual_revenue=55600.0,
        total_records=4,
    )
    result = service.calculate_revenue_deficit(agg)

    assert result.total_planned_revenue == 70000.0
    assert result.total_actual_revenue == 55600.0
    assert result.total_revenue_deficit == 14400.0
    assert result.has_deficit is True
    assert "Revenue deficit identified" in result.summary


def test_calculate_revenue_deficit_surplus():
    service = AdvancedMetricsService()
    agg = RevenueDeficitAggregation(
        total_planned_revenue=50000.0,
        total_actual_revenue=60000.0,
        total_records=2,
    )
    result = service.calculate_revenue_deficit(agg)

    assert result.total_planned_revenue == 50000.0
    assert result.total_actual_revenue == 60000.0
    assert result.total_revenue_deficit == -10000.0
    assert result.has_deficit is False
    assert "No revenue deficit" in result.summary


def test_calculate_revenue_deficit_empty():
    service = AdvancedMetricsService()
    result = service.calculate_revenue_deficit(None)
    assert result.total_planned_revenue == 0.0
    assert result.total_actual_revenue == 0.0
    assert result.has_deficit is False


def test_calculate_average_discount():
    service = AdvancedMetricsService()
    agg = AverageDiscountAggregation(
        total_planned_revenue=70000.0,
        total_actual_revenue=55600.0,
        total_discount_value=14400.0,
        overall_average_discount_percentage=15.0,
        discount_by_promotion={"Promo_Flash": 20.0, "Promo_B2B": 10.0},
        total_records=4,
    )
    result = service.calculate_average_discount(agg)

    assert result.overall_average_discount_percentage == 15.0
    assert result.total_discount_value == 14400.0
    assert "Promo_Flash" in result.discount_by_promotion
    assert result.discount_by_promotion["Promo_Flash"] == 20.0


def test_calculate_average_discount_empty():
    service = AdvancedMetricsService()
    result = service.calculate_average_discount(None)
    assert result.overall_average_discount_percentage == 0.0
    assert result.total_discount_value == 0.0
    assert result.discount_by_promotion == {}


def test_identify_sales_seasonality():
    service = AdvancedMetricsService()
    agg = SeasonalityAggregation(
        monthly_volumes={"2023-01": 300.0, "2023-02": 100.0, "2023-03": 60.0},
        total_records=4,
    )
    result = service.identify_sales_seasonality(agg)

    assert result.peak_month == "2023-01"
    assert result.peak_volume == 300.0
    assert result.lowest_month == "2023-03"
    assert result.lowest_volume == 60.0
    assert "Peak sales volume occurred in 2023-01" in result.seasonality_pattern


def test_identify_sales_seasonality_empty():
    service = AdvancedMetricsService()
    result = service.identify_sales_seasonality(None)
    assert result.peak_month == "N/A"
    assert result.peak_volume == 0.0
    assert result.seasonality_pattern == "No data to analyze"


def test_calculate_price_elasticity():
    service = AdvancedMetricsService()
    agg = PriceElasticityAggregation(
        promoted_avg_price=80.0,
        non_promoted_avg_price=100.0,
        promoted_avg_qty=220.0,
        non_promoted_avg_qty=80.0,
        promoted_count=2,
        non_promoted_count=2,
        total_records=4,
    )
    result = service.calculate_price_elasticity(agg)

    # % delta price = (80 - 100) / 100 = -20%
    # % delta qty = (220 - 80) / 80 = +175%
    # Elasticity = 175 / -20 = -8.75
    assert result.elasticity_coefficient == -8.75
    assert result.percentage_change_in_price == -20.0
    assert result.percentage_change_in_quantity == 175.0
    assert "Elastic" in result.demand_classification


def test_calculate_price_elasticity_empty():
    service = AdvancedMetricsService()
    result = service.calculate_price_elasticity(None)
    assert result.elasticity_coefficient == 0.0
    assert result.demand_classification == "Undefined"
