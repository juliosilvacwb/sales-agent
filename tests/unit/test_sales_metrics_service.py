"""Unit tests for SalesMetricsApplicationService using mocked Ports."""
from datetime import date
from unittest.mock import MagicMock
import pytest

from src.application.port.outbound.sales_data_port import SalesDataPort
from src.application.service.sales_metrics_service import SalesMetricsApplicationService
from src.domain.model.sale_record import SaleRecord


@pytest.fixture
def mock_sales_port():
    port = MagicMock(spec=SalesDataPort)
    sample_records = [
        SaleRecord(
            product_id="Prod_A",
            local="Whse_1",
            date=date(2023, 1, 10),
            planned_quantity=100.0,
            actual_quantity=120.0,
            planned_price=50.0,
            actual_price=45.0,
            service_level=0.95,
            promotion_type="Promo10",
        ),
        SaleRecord(
            product_id="Prod_B",
            local="Whse_2",
            date=date(2023, 2, 15),
            planned_quantity=200.0,
            actual_quantity=180.0,
            planned_price=100.0,
            actual_price=100.0,
            service_level=0.88,
            promotion_type=None,
        ),
    ]
    port.get_all_sales.return_value = sample_records
    port.execute_read_only_query.return_value = [{"col1": "val1", "count": 42}]
    return port


@pytest.fixture
def application_service(mock_sales_port):
    return SalesMetricsApplicationService(sales_data_port=mock_sales_port)


def test_get_top_selling_product(application_service, mock_sales_port):
    result = application_service.get_top_selling_product()
    mock_sales_port.get_all_sales.assert_called_once()
    assert result.product_id == "Prod_B"
    assert result.total_quantity == 180.0


def test_get_top_locations_by_volume(application_service, mock_sales_port):
    result = application_service.get_top_locations_by_volume(limit=2)
    mock_sales_port.get_all_sales.assert_called_once()
    assert len(result.top_locations) == 2
    assert result.primary_location == "Whse_2"


def test_get_total_sales_in_period(application_service, mock_sales_port):
    result = application_service.get_total_sales_in_period(
        start_date=date(2023, 1, 1), end_date=date(2023, 1, 31)
    )
    mock_sales_port.get_all_sales.assert_called_once()
    assert result.total_quantity == 120.0
    assert result.total_records == 1


def test_compare_planned_vs_actual_quantity(application_service, mock_sales_port):
    result = application_service.compare_planned_vs_actual_quantity()
    mock_sales_port.get_all_sales.assert_called_once()
    assert result.total_planned_quantity == 300.0
    assert result.total_actual_quantity == 300.0
    assert result.difference_quantity == 0.0


def test_analyze_promotion_impact(application_service, mock_sales_port):
    result = application_service.analyze_promotion_impact()
    mock_sales_port.get_all_sales.assert_called_once()
    assert result.promoted_sales_count == 1
    assert result.non_promoted_sales_count == 1


def test_analyze_service_level_bottlenecks(application_service, mock_sales_port):
    result = application_service.analyze_service_level_bottlenecks()
    mock_sales_port.get_all_sales.assert_called_once()
    assert result.worst_location == "Whse_2"
    assert result.worst_service_level == 0.88


def test_calculate_revenue_deficit(application_service, mock_sales_port):
    result = application_service.calculate_revenue_deficit()
    mock_sales_port.get_all_sales.assert_called_once()
    # Planned: (100*50) + (200*100) = 25000. Actual: (120*45) + (180*100) = 5400 + 18000 = 23400. Deficit: 1600.
    assert result.total_planned_revenue == 25000.0
    assert result.total_actual_revenue == 23400.0
    assert result.total_revenue_deficit == 1600.0
    assert result.has_deficit is True


def test_calculate_average_discount(application_service, mock_sales_port):
    result = application_service.calculate_average_discount()
    mock_sales_port.get_all_sales.assert_called_once()
    # Discount rates: (50-45)/50 = 10% (positive discount). Record 2 has 0% discount.
    # Per business logic (Incident B002), average discount percentage considers positive discounts.
    assert result.overall_average_discount_percentage == 10.0


def test_identify_sales_seasonality(application_service, mock_sales_port):
    result = application_service.identify_sales_seasonality()
    mock_sales_port.get_all_sales.assert_called_once()
    assert result.peak_month == "2023-02"
    assert result.peak_volume == 180.0


def test_calculate_price_elasticity(application_service, mock_sales_port):
    result = application_service.calculate_price_elasticity()
    mock_sales_port.get_all_sales.assert_called_once()
    assert result.elasticity_coefficient != 0.0


def test_execute_custom_query(application_service, mock_sales_port):
    raw_sql = "SELECT local, SUM(actual_quantity) FROM sales_data GROUP BY local"
    result = application_service.execute_custom_query(raw_sql)
    mock_sales_port.execute_read_only_query.assert_called_once_with(raw_sql)
    assert result == [{"col1": "val1", "count": 42}]
