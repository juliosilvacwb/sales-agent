"""Unit tests for BasicMetricsService."""
from datetime import date
import pytest
from src.domain.model.sale_record import SaleRecord
from src.domain.service.basic_metrics_service import BasicMetricsService


@pytest.fixture
def sample_sales_records():
    return [
        SaleRecord(
            product_id="Product_01",
            local="Whse_A",
            date=date(2023, 1, 1),
            planned_quantity=100.0,
            actual_quantity=150.0,
            planned_price=10.0,
            actual_price=10.0,
            service_level=0.98,
            promotion_type=None,
        ),
        SaleRecord(
            product_id="Product_01",
            local="Whse_B",
            date=date(2023, 1, 15),
            planned_quantity=200.0,
            actual_quantity=250.0,
            planned_price=10.0,
            actual_price=8.0,
            service_level=0.95,
            promotion_type="Promo_Winter",
        ),
        SaleRecord(
            product_id="Product_02",
            local="Whse_A",
            date=date(2023, 2, 1),
            planned_quantity=300.0,
            actual_quantity=100.0,
            planned_price=20.0,
            actual_price=20.0,
            service_level=0.90,
            promotion_type="None",
        ),
    ]


def test_get_top_selling_product(sample_sales_records):
    service = BasicMetricsService()
    result = service.get_top_selling_product(sample_sales_records)

    # Product_01 has 150 + 250 = 400. Product_02 has 100.
    assert result.product_id == "Product_01"
    assert result.total_quantity == 400.0
    assert result.total_revenue == (150 * 10.0) + (250 * 8.0)
    assert result.total_records == 2


def test_get_top_selling_product_empty():
    service = BasicMetricsService()
    result = service.get_top_selling_product([])
    assert result.product_id == "N/A"
    assert result.total_quantity == 0.0


def test_get_top_locations_by_volume(sample_sales_records):
    service = BasicMetricsService()
    result = service.get_top_locations_by_volume(sample_sales_records, limit=2)

    # Whse_A: 150 + 100 = 250. Whse_B: 250.
    assert len(result.top_locations) == 2
    assert result.primary_location in ["Whse_A", "Whse_B"]
    assert result.primary_quantity == 250.0


def test_get_total_sales_in_period(sample_sales_records):
    service = BasicMetricsService()
    
    # Overall
    res_all = service.get_total_sales_in_period(sample_sales_records)
    assert res_all.total_quantity == 500.0
    assert res_all.total_records == 3
    assert res_all.total_revenue == (150 * 10) + (250 * 8) + (100 * 20)  # 1500 + 2000 + 2000 = 5500

    # Filtered by January 2023
    res_jan = service.get_total_sales_in_period(
        sample_sales_records, start_date=date(2023, 1, 1), end_date=date(2023, 1, 31)
    )
    assert res_jan.total_quantity == 400.0
    assert res_jan.total_records == 2


def test_compare_planned_vs_actual_quantity(sample_sales_records):
    service = BasicMetricsService()
    result = service.compare_planned_vs_actual_quantity(sample_sales_records)

    # Planned: 100 + 200 + 300 = 600. Actual: 150 + 250 + 100 = 500.
    assert result.total_planned_quantity == 600.0
    assert result.total_actual_quantity == 500.0
    assert result.difference_quantity == -100.0
    assert round(result.achievement_percentage, 1) == 83.3
    assert "missed" in result.evaluation.lower()


def test_analyze_promotion_impact(sample_sales_records):
    service = BasicMetricsService()
    result = service.analyze_promotion_impact(sample_sales_records)

    assert result.promoted_sales_count == 1
    assert result.non_promoted_sales_count == 2
    assert result.promoted_total_quantity == 250.0
    assert result.non_promoted_total_quantity == 250.0
    assert result.promoted_avg_actual_price == 8.0
    assert result.average_discount_in_promotion == 20.0
