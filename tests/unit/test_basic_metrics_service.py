"""Unit tests for BasicMetricsService using aggregated data structures."""
from datetime import date
import pytest

from src.domain.model.aggregation_models import (
    LocationSalesAggregation,
    PlannedVsActualAggregation,
    ProductAggregation,
    PromotionImpactAggregation,
    TotalSalesAggregation,
)
from src.domain.service.basic_metrics_service import BasicMetricsService


def test_get_top_selling_product():
    service = BasicMetricsService()
    agg = ProductAggregation(
        product_id="Product_01",
        total_quantity=400.0,
        total_revenue=3500.0,
        total_records=2,
    )
    result = service.get_top_selling_product(agg)

    assert result.product_id == "Product_01"
    assert result.total_quantity == 400.0
    assert result.total_revenue == 3500.0
    assert result.total_records == 2


def test_get_top_selling_product_empty():
    service = BasicMetricsService()
    result = service.get_top_selling_product(None)
    assert result.product_id == "N/A"
    assert result.total_quantity == 0.0
    assert result.total_records == 0


def test_get_top_locations_by_volume():
    service = BasicMetricsService()
    aggregations = [
        LocationSalesAggregation(local="Whse_A", total_quantity=250.0, total_revenue=3500.0),
        LocationSalesAggregation(local="Whse_B", total_quantity=250.0, total_revenue=2000.0),
    ]
    result = service.get_top_locations_by_volume(aggregations, limit=2)

    assert len(result.top_locations) == 2
    assert result.primary_location == "Whse_A"
    assert result.primary_quantity == 250.0
    assert result.top_locations[0]["local"] == "Whse_A"
    assert result.top_locations[1]["local"] == "Whse_B"


def test_get_top_locations_by_volume_empty():
    service = BasicMetricsService()
    result = service.get_top_locations_by_volume([])
    assert result.top_locations == []
    assert result.primary_location is None
    assert result.primary_quantity == 0.0


def test_get_total_sales_in_period():
    service = BasicMetricsService()

    # Overall
    agg = TotalSalesAggregation(total_quantity=500.0, total_revenue=5500.0, total_records=3)
    res_all = service.get_total_sales_in_period(agg)
    assert res_all.total_quantity == 500.0
    assert res_all.total_records == 3
    assert res_all.total_revenue == 5500.0
    assert res_all.average_ticket == 11.0

    # Filtered by date
    agg_jan = TotalSalesAggregation(total_quantity=400.0, total_revenue=3500.0, total_records=2)
    res_jan = service.get_total_sales_in_period(
        agg_jan, start_date=date(2023, 1, 1), end_date=date(2023, 1, 31)
    )
    assert res_jan.total_quantity == 400.0
    assert res_jan.total_records == 2
    assert res_jan.period_start == "01/01/2023"
    assert res_jan.period_end == "31/01/2023"
    assert res_jan.average_ticket == 8.75


def test_get_total_sales_in_period_empty():
    service = BasicMetricsService()
    res = service.get_total_sales_in_period(None)
    assert res.total_quantity == 0.0
    assert res.total_revenue == 0.0
    assert res.total_records == 0


def test_compare_planned_vs_actual_quantity():
    service = BasicMetricsService()
    agg = PlannedVsActualAggregation(
        total_planned_quantity=600.0,
        total_actual_quantity=500.0,
        total_records=3,
    )
    result = service.compare_planned_vs_actual_quantity(agg)

    assert result.total_planned_quantity == 600.0
    assert result.total_actual_quantity == 500.0
    assert result.difference_quantity == -100.0
    assert round(result.achievement_percentage, 1) == 83.3
    assert "missed" in result.evaluation.lower()


def test_compare_planned_vs_actual_quantity_exceeded():
    service = BasicMetricsService()
    agg = PlannedVsActualAggregation(
        total_planned_quantity=500.0,
        total_actual_quantity=600.0,
        total_records=3,
    )
    result = service.compare_planned_vs_actual_quantity(agg)

    assert result.total_planned_quantity == 500.0
    assert result.total_actual_quantity == 600.0
    assert result.difference_quantity == 100.0
    assert result.achievement_percentage == 120.0
    assert "exceeded" in result.evaluation.lower()


def test_analyze_promotion_impact():
    service = BasicMetricsService()
    agg = PromotionImpactAggregation(
        promoted_sales_count=1,
        non_promoted_sales_count=2,
        promoted_total_quantity=250.0,
        non_promoted_total_quantity=250.0,
        promoted_avg_actual_price=8.0,
        non_promoted_avg_actual_price=15.0,
        average_discount_in_promotion=20.0,
        total_records=3,
    )
    result = service.analyze_promotion_impact(agg)

    assert result.promoted_sales_count == 1
    assert result.non_promoted_sales_count == 2
    assert result.promoted_total_quantity == 250.0
    assert result.non_promoted_total_quantity == 250.0
    assert result.promoted_avg_actual_price == 8.0
    assert result.average_discount_in_promotion == 20.0
    assert result.volume_lift_percentage == 100.0
    assert "Promotions generated" in result.summary


def test_analyze_promotion_impact_empty():
    service = BasicMetricsService()
    result = service.analyze_promotion_impact(None)
    assert result.promoted_sales_count == 0
    assert result.non_promoted_sales_count == 0
    assert result.summary == "No records to analyze"
