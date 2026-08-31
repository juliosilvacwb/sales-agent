"""Integration tests ensuring result parity and end-to-end correctness of analytical engine scalability."""
from datetime import date
import os
import tempfile
import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import SalesMetricsApplicationService
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService


@pytest.fixture
def test_dataset():
    """Provides a synthetic CSV dataset representing realistic multi-product sales."""
    content = (
        "product_id;local;date;planned_quantity;actual_quantity;planned_price;promotion_type;actual_price;service_level\n"
        "Product_Alpha;Whse_North;05/01/2023;100;120;50.0;Promo_Winter;45.0;0.98\n"
        "Product_Alpha;Whse_South;15/01/2023;100;80;50.0;None;50.0;0.92\n"
        "Product_Beta;Whse_North;10/02/2023;200;220;100.0;Promo_Flash;80.0;0.85\n"
        "Product_Beta;Whse_South;25/02/2023;150;100;100.0;;100.0;0.80\n"
        "Product_Gamma;Whse_North;12/03/2023;50;60;200.0;Promo_B2B;180.0;0.95\n"
        "Product_Gamma;Whse_South;20/03/2023;50;40;200.0;None;200.0;0.99\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sales_application_service(test_dataset):
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=test_dataset)
    basic_service = BasicMetricsService()
    advanced_service = AdvancedMetricsService()
    return SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=basic_service,
        advanced_metrics_service=advanced_service,
    )


def test_integration_top_selling_product(sales_application_service):
    """Verifies top selling product computation pushdown."""
    # Alpha: 120 + 80 = 200
    # Beta: 220 + 100 = 320 (Top)
    # Gamma: 60 + 40 = 100
    result = sales_application_service.get_top_selling_product()
    assert result.product_id == "Product_Beta"
    assert result.total_quantity == 320.0
    # Revenue: (220 * 80) + (100 * 100) = 17600 + 10000 = 27600
    assert result.total_revenue == 27600.0
    assert result.total_records == 2


def test_integration_top_locations_by_volume(sales_application_service):
    """Verifies top locations ranking pushdown."""
    # Whse_North: 120 + 220 + 60 = 400
    # Whse_South: 80 + 100 + 40 = 220
    result = sales_application_service.get_top_locations_by_volume(limit=2)
    assert len(result.top_locations) == 2
    assert result.primary_location == "Whse_North"
    assert result.primary_quantity == 400.0
    assert result.top_locations[0]["local"] == "Whse_North"
    assert result.top_locations[0]["total_quantity"] == 400.0
    assert result.top_locations[1]["local"] == "Whse_South"
    assert result.top_locations[1]["total_quantity"] == 220.0


def test_integration_total_sales_in_period(sales_application_service):
    """Verifies total sales period filtering pushdown."""
    # Total overall: 400 + 220 = 620 units
    res_overall = sales_application_service.get_total_sales_in_period()
    assert res_overall.total_quantity == 620.0
    assert res_overall.total_records == 6

    # Filtered January: 120 + 80 = 200 units
    res_jan = sales_application_service.get_total_sales_in_period(
        start_date=date(2023, 1, 1), end_date=date(2023, 1, 31)
    )
    assert res_jan.total_quantity == 200.0
    assert res_jan.total_records == 2
    # Rev: (120*45) + (80*50) = 5400 + 4000 = 9400
    assert res_jan.total_revenue == 9400.0
    assert res_jan.average_ticket == 47.0


def test_integration_compare_planned_vs_actual_quantity(sales_application_service):
    """Verifies planned vs actual quantity pushdown."""
    # Planned: 100+100+200+150+50+50 = 650
    # Actual: 120+80+220+100+60+40 = 620
    # Diff: -30
    result = sales_application_service.compare_planned_vs_actual_quantity()
    assert result.total_planned_quantity == 650.0
    assert result.total_actual_quantity == 620.0
    assert result.difference_quantity == -30.0
    assert round(result.achievement_percentage, 1) == 95.4
    assert "missed" in result.evaluation.lower()


def test_integration_analyze_promotion_impact(sales_application_service):
    """Verifies promotion impact aggregation pushdown."""
    # Promoted rows: Winter (Alpha, 120 @ 45, plan 50 -> 10% disc), Flash (Beta, 220 @ 80, plan 100 -> 20% disc), B2B (Gamma, 60 @ 180, plan 200 -> 10% disc)
    # Count: 3
    # Non-promoted: 3 (80 + 100 + 40 = 220)
    result = sales_application_service.analyze_promotion_impact()
    assert result.promoted_sales_count == 3
    assert result.non_promoted_sales_count == 3
    assert result.promoted_total_quantity == 400.0
    assert result.non_promoted_total_quantity == 220.0
    # Avg disc in promo: (10 + 20 + 10) / 3 = 13.33%
    assert round(result.average_discount_in_promotion, 2) == 13.33
    assert result.volume_lift_percentage > 0


def test_integration_analyze_service_level_bottlenecks(sales_application_service):
    """Verifies SLA bottleneck detection pushdown."""
    # North: (0.98 + 0.85 + 0.95) / 3 = 0.9267
    # South: (0.92 + 0.80 + 0.99) / 3 = 0.9033 (Worst)
    result = sales_application_service.analyze_service_level_bottlenecks()
    assert result.worst_location == "Whse_South"
    assert round(result.worst_service_level, 3) == 0.903
    assert "Whse_South" in result.summary


def test_integration_calculate_revenue_deficit(sales_application_service):
    """Verifies financial loss/deficit computation pushdown."""
    # Planned Rev: (100*50) + (100*50) + (200*100) + (150*100) + (50*200) + (50*200) = 5000+5000+20000+15000+10000+10000 = 65000
    # Actual Rev: (120*45) + (80*50) + (220*80) + (100*100) + (60*180) + (40*200) = 5400+4000+17600+10000+10800+8000 = 55800
    # Deficit: 65000 - 55800 = 9200
    result = sales_application_service.calculate_revenue_deficit()
    assert result.total_planned_revenue == 65000.0
    assert result.total_actual_revenue == 55800.0
    assert result.total_revenue_deficit == 9200.0
    assert result.has_deficit is True
    assert "Revenue deficit identified" in result.summary


def test_integration_calculate_average_discount(sales_application_service):
    """Verifies average discount margins pushdown."""
    result = sales_application_service.calculate_average_discount()
    assert result.total_planned_revenue == 65000.0
    assert result.total_actual_revenue == 55800.0
    assert result.total_discount_value == 6200.0
    assert round(result.overall_average_discount_percentage, 2) == 13.33
    assert "Promo_Winter" in result.discount_by_promotion
    assert "Promo_Flash" in result.discount_by_promotion
    assert "Promo_B2B" in result.discount_by_promotion


def test_integration_identify_sales_seasonality(sales_application_service):
    """Verifies monthly volume seasonality pushdown."""
    # Jan: 120 + 80 = 200
    # Feb: 220 + 100 = 320 (Peak)
    # Mar: 60 + 40 = 100 (Lowest)
    result = sales_application_service.identify_sales_seasonality()
    assert result.peak_month == "2023-02"
    assert result.peak_volume == 320.0
    assert result.lowest_month == "2023-03"
    assert result.lowest_volume == 100.0


def test_integration_calculate_price_elasticity(sales_application_service):
    """Verifies Price Elasticity calculation pushdown for catalog overview and single product."""
    catalog_result = sales_application_service.calculate_price_elasticity()
    assert catalog_result.total_products_evaluated == 3
    assert catalog_result.inconclusive_products_count == 0
    assert len(catalog_result.most_elastic_products) == 3

    beta_result = sales_application_service.calculate_price_elasticity(product_id="Product_Beta")
    assert beta_result.product_id == "Product_Beta"
    assert beta_result.elasticity_coefficient == -6.0
    assert beta_result.percentage_change_in_price == -20.0
    assert beta_result.percentage_change_in_quantity == 120.0
    assert "Elastic" in beta_result.demand_classification

