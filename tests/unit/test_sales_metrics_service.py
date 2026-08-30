"""Unit tests for SalesMetricsApplicationService using mocked Ports."""
from datetime import date
from unittest.mock import MagicMock
import pytest

from src.application.port.outbound.sales_data_port import SalesDataPort
from src.application.service.sales_metrics_service import SalesMetricsApplicationService
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


@pytest.fixture
def mock_sales_port():
    port = MagicMock(spec=SalesDataPort)
    port.aggregate_top_selling_product.return_value = ProductAggregation(
        product_id="Prod_B",
        total_quantity=180.0,
        total_revenue=18000.0,
        total_records=1,
    )
    port.aggregate_top_locations.return_value = [
        LocationSalesAggregation(local="Whse_2", total_quantity=180.0, total_revenue=18000.0),
        LocationSalesAggregation(local="Whse_1", total_quantity=120.0, total_revenue=5400.0),
    ]
    port.aggregate_total_sales.return_value = TotalSalesAggregation(
        total_quantity=120.0,
        total_revenue=5400.0,
        total_records=1,
    )
    port.aggregate_planned_vs_actual.return_value = PlannedVsActualAggregation(
        total_planned_quantity=300.0,
        total_actual_quantity=300.0,
        total_records=2,
    )
    port.aggregate_promotion_impact.return_value = PromotionImpactAggregation(
        promoted_sales_count=1,
        non_promoted_sales_count=1,
        promoted_total_quantity=120.0,
        non_promoted_total_quantity=180.0,
        promoted_avg_actual_price=45.0,
        non_promoted_avg_actual_price=100.0,
        average_discount_in_promotion=10.0,
        total_records=2,
    )
    port.aggregate_service_level_bottlenecks.return_value = ServiceLevelBottleneckAggregation(
        location_averages={"Whse_1": 0.95, "Whse_2": 0.88},
        overall_average_service_level=0.915,
        total_records=2,
    )
    port.aggregate_revenue_deficit.return_value = RevenueDeficitAggregation(
        total_planned_revenue=25000.0,
        total_actual_revenue=23400.0,
        total_records=2,
    )
    port.aggregate_average_discount.return_value = AverageDiscountAggregation(
        total_planned_revenue=25000.0,
        total_actual_revenue=23400.0,
        total_discount_value=1600.0,
        overall_average_discount_percentage=10.0,
        discount_by_promotion={"Promo10": 10.0},
        total_records=2,
    )
    port.aggregate_seasonality.return_value = SeasonalityAggregation(
        monthly_volumes={"2023-01": 120.0, "2023-02": 180.0},
        total_records=2,
    )
    port.aggregate_price_elasticity.return_value = PriceElasticityAggregation(
        promoted_avg_price=45.0,
        non_promoted_avg_price=100.0,
        promoted_avg_qty=120.0,
        non_promoted_avg_qty=180.0,
        promoted_count=1,
        non_promoted_count=1,
        total_records=2,
    )
    port.execute_read_only_query.return_value = [{"col1": "val1", "count": 42}]
    return port


@pytest.fixture
def application_service(mock_sales_port):
    return SalesMetricsApplicationService(sales_data_port=mock_sales_port)


def test_get_top_selling_product(application_service, mock_sales_port):
    result = application_service.get_top_selling_product()
    mock_sales_port.aggregate_top_selling_product.assert_called_once()
    assert result.product_id == "Prod_B"
    assert result.total_quantity == 180.0


def test_get_top_locations_by_volume(application_service, mock_sales_port):
    result = application_service.get_top_locations_by_volume(limit=2)
    mock_sales_port.aggregate_top_locations.assert_called_once_with(limit=2)
    assert len(result.top_locations) == 2
    assert result.primary_location == "Whse_2"


def test_get_total_sales_in_period(application_service, mock_sales_port):
    result = application_service.get_total_sales_in_period(
        start_date=date(2023, 1, 1), end_date=date(2023, 1, 31)
    )
    mock_sales_port.aggregate_total_sales.assert_called_once_with(
        start_date=date(2023, 1, 1), end_date=date(2023, 1, 31)
    )
    assert result.total_quantity == 120.0
    assert result.total_records == 1


def test_compare_planned_vs_actual_quantity(application_service, mock_sales_port):
    result = application_service.compare_planned_vs_actual_quantity()
    mock_sales_port.aggregate_planned_vs_actual.assert_called_once()
    assert result.total_planned_quantity == 300.0
    assert result.total_actual_quantity == 300.0
    assert result.difference_quantity == 0.0


def test_analyze_promotion_impact(application_service, mock_sales_port):
    result = application_service.analyze_promotion_impact()
    mock_sales_port.aggregate_promotion_impact.assert_called_once()
    assert result.promoted_sales_count == 1
    assert result.non_promoted_sales_count == 1


def test_analyze_service_level_bottlenecks(application_service, mock_sales_port):
    result = application_service.analyze_service_level_bottlenecks()
    mock_sales_port.aggregate_service_level_bottlenecks.assert_called_once()
    assert result.worst_location == "Whse_2"
    assert result.worst_service_level == 0.88


def test_calculate_revenue_deficit(application_service, mock_sales_port):
    result = application_service.calculate_revenue_deficit()
    mock_sales_port.aggregate_revenue_deficit.assert_called_once()
    assert result.total_planned_revenue == 25000.0
    assert result.total_actual_revenue == 23400.0
    assert result.total_revenue_deficit == 1600.0
    assert result.has_deficit is True


def test_calculate_average_discount(application_service, mock_sales_port):
    result = application_service.calculate_average_discount()
    mock_sales_port.aggregate_average_discount.assert_called_once()
    assert result.overall_average_discount_percentage == 10.0


def test_identify_sales_seasonality(application_service, mock_sales_port):
    result = application_service.identify_sales_seasonality()
    mock_sales_port.aggregate_seasonality.assert_called_once()
    assert result.peak_month == "2023-02"
    assert result.peak_volume == 180.0


def test_calculate_price_elasticity(application_service, mock_sales_port):
    result = application_service.calculate_price_elasticity()
    mock_sales_port.aggregate_price_elasticity.assert_called_once()
    assert result.elasticity_coefficient != 0.0


def test_execute_custom_query(application_service, mock_sales_port):
    raw_sql = "SELECT local, SUM(actual_quantity) FROM sales_data GROUP BY local"
    result = application_service.execute_custom_query(raw_sql)
    mock_sales_port.execute_read_only_query.assert_called_once_with(raw_sql)
    assert result == [{"col1": "val1", "count": 42}]


def test_usecase_orchestration_all_analytical_methods(application_service, mock_sales_port):
    """Verify that all analytical methods delegate to aggregation methods on port (TEST003-16)."""
    application_service.get_top_selling_product()
    application_service.get_top_locations_by_volume(limit=3)
    application_service.get_total_sales_in_period(start_date=date(2023, 1, 1), end_date=date(2023, 1, 31))
    application_service.compare_planned_vs_actual_quantity()
    application_service.analyze_promotion_impact()
    application_service.analyze_service_level_bottlenecks()
    application_service.calculate_revenue_deficit()
    application_service.calculate_average_discount()
    application_service.identify_sales_seasonality()
    application_service.calculate_price_elasticity()

    mock_sales_port.aggregate_top_selling_product.assert_called()
    mock_sales_port.aggregate_top_locations.assert_called_with(limit=3)
    mock_sales_port.aggregate_total_sales.assert_called_with(start_date=date(2023, 1, 1), end_date=date(2023, 1, 31))
    mock_sales_port.aggregate_planned_vs_actual.assert_called()
    mock_sales_port.aggregate_promotion_impact.assert_called()
    mock_sales_port.aggregate_service_level_bottlenecks.assert_called()
    mock_sales_port.aggregate_revenue_deficit.assert_called()
    mock_sales_port.aggregate_average_discount.assert_called()
    mock_sales_port.aggregate_seasonality.assert_called()
    mock_sales_port.aggregate_price_elasticity.assert_called()
