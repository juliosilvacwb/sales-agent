"""Unit tests for AdvancedMetricsService."""
from datetime import date
import pytest
from src.domain.model.sale_record import SaleRecord
from src.domain.service.advanced_metrics_service import AdvancedMetricsService


@pytest.fixture
def sample_advanced_sales_records():
    return [
        SaleRecord(
            product_id="Product_01",
            local="Whse_A",
            date=date(2023, 1, 1),
            planned_quantity=100.0,
            actual_quantity=80.0,
            planned_price=100.0,
            actual_price=100.0,
            service_level=0.98,
            promotion_type=None,
        ),
        SaleRecord(
            product_id="Product_01",
            local="Whse_B",
            date=date(2023, 1, 15),
            planned_quantity=200.0,
            actual_quantity=220.0,
            planned_price=100.0,
            actual_price=80.0,
            service_level=0.85,
            promotion_type="Promo_Flash",
        ),
        SaleRecord(
            product_id="Product_02",
            local="Whse_B",
            date=date(2023, 2, 10),
            planned_quantity=150.0,
            actual_quantity=100.0,
            planned_price=200.0,
            actual_price=180.0,
            service_level=0.80,
            promotion_type="Promo_B2B",
        ),
        SaleRecord(
            product_id="Product_02",
            local="Whse_A",
            date=date(2023, 3, 20),
            planned_quantity=50.0,
            actual_quantity=60.0,
            planned_price=200.0,
            actual_price=200.0,
            service_level=0.99,
            promotion_type=None,
        ),
    ]


def test_analyze_service_level_bottlenecks(sample_advanced_sales_records):
    service = AdvancedMetricsService()
    result = service.analyze_service_level_bottlenecks(sample_advanced_sales_records)

    # Whse_A: (0.98 + 0.99) / 2 = 0.985
    # Whse_B: (0.85 + 0.80) / 2 = 0.825
    assert result.worst_location == "Whse_B"
    assert round(result.worst_service_level, 3) == 0.825
    assert "Whse_B" in result.summary


def test_calculate_revenue_deficit(sample_advanced_sales_records):
    service = AdvancedMetricsService()
    result = service.calculate_revenue_deficit(sample_advanced_sales_records)

    assert result.total_planned_revenue == 70000.0
    assert result.total_actual_revenue == 55600.0
    assert result.total_revenue_deficit == 14400.0
    assert result.has_deficit is True


def test_calculate_average_discount(sample_advanced_sales_records):
    service = AdvancedMetricsService()
    result = service.calculate_average_discount(sample_advanced_sales_records)

    assert result.overall_average_discount_percentage == 15.0
    assert result.total_discount_value == 14400.0
    assert "Promo_Flash" in result.discount_by_promotion
    assert result.discount_by_promotion["Promo_Flash"] == 20.0


def test_calculate_average_discount_mixed_price_increases():
    service = AdvancedMetricsService()
    records = [
        SaleRecord(
            product_id="P1",
            local="Whse_A",
            date=date(2023, 1, 1),
            planned_quantity=100.0,
            actual_quantity=100.0,
            planned_price=100.0,
            actual_price=80.0,  # 20% discount, discount_val = 2,000
            service_level=0.9,
            promotion_type="Flash",
        ),
        SaleRecord(
            product_id="P2",
            local="Whse_A",
            date=date(2023, 1, 1),
            planned_quantity=100.0,
            actual_quantity=100.0,
            planned_price=100.0,
            actual_price=150.0,  # Price increase, negative discount
            service_level=0.9,
            promotion_type=None,
        ),
    ]
    result = service.calculate_average_discount(records)
    # Price increase shouldn't negate the 2,000 discount or lower the positive discount percentage
    assert result.total_discount_value == 2000.0
    assert result.overall_average_discount_percentage == 20.0
    assert result.discount_by_promotion == {"Flash": 20.0}



def test_identify_sales_seasonality(sample_advanced_sales_records):
    service = AdvancedMetricsService()
    result = service.identify_sales_seasonality(sample_advanced_sales_records)

    # 2023-01: 80 + 220 = 300
    # 2023-02: 100
    # 2023-03: 60
    assert result.peak_month == "2023-01"
    assert result.peak_volume == 300.0
    assert result.lowest_month == "2023-03"
    assert result.lowest_volume == 60.0


def test_calculate_price_elasticity(sample_advanced_sales_records):
    service = AdvancedMetricsService()
    result = service.calculate_price_elasticity(sample_advanced_sales_records)

    assert result.elasticity_coefficient < 0
    assert "Elastic" in result.demand_classification


def test_analyze_service_level_bottlenecks_equal_sla():
    service = AdvancedMetricsService()
    records = [
        SaleRecord("P1", "Whse_A", date(2023, 1, 1), 10, 10, 10, 10, 0.98),
        SaleRecord("P1", "Whse_B", date(2023, 1, 1), 10, 10, 10, 10, 0.98),
        SaleRecord("P1", "Whse_C", date(2023, 1, 1), 10, 10, 10, 10, 0.98),
    ]
    result = service.analyze_service_level_bottlenecks(records)

    assert result.worst_location == "N/A"
    assert result.worst_service_level == 0.98
    assert result.overall_average_service_level == 0.98
    assert "No logistics SLA bottleneck identified" in result.summary


def test_analyze_service_level_bottlenecks_floating_imprecision():
    service = AdvancedMetricsService()
    records = [
        SaleRecord("P1", "Whse_A", date(2023, 1, 1), 10, 10, 10, 10, 0.9799999999996978),
        SaleRecord("P1", "Whse_B", date(2023, 1, 1), 10, 10, 10, 10, 0.9800000000003375),
    ]
    result = service.analyze_service_level_bottlenecks(records)

    assert result.worst_location == "N/A"
    assert result.worst_service_level == 0.98
    assert "No logistics SLA bottleneck identified" in result.summary


def test_analyze_service_level_bottlenecks_single_location():
    service = AdvancedMetricsService()
    records = [
        SaleRecord("P1", "Whse_A", date(2023, 1, 1), 10, 10, 10, 10, 0.95),
        SaleRecord("P2", "Whse_A", date(2023, 1, 2), 20, 20, 10, 10, 0.95),
    ]
    result = service.analyze_service_level_bottlenecks(records)

    assert result.worst_location == "N/A"
    assert result.worst_service_level == 0.95
    assert result.overall_average_service_level == 0.95
    assert "No logistics SLA bottleneck identified" in result.summary


