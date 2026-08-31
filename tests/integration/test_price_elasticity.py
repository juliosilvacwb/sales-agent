"""Integration tests for Segment-Based Price Elasticity of Demand (T008 / R008)."""
import os
import tempfile
import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import SalesMetricsApplicationService
from src.domain.model.metric_result import (
    CatalogPriceElasticityOverview,
    PriceElasticityResult,
)
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService


@pytest.fixture
def elasticity_dataset():
    """Provides a synthetic CSV dataset with varied product elasticity behaviors."""
    content = (
        "product_id;local;date;planned_quantity;actual_quantity;planned_price;promotion_type;actual_price;service_level\n"
        # PROD_ELASTIC: Base price 100, qty 100. Promo price 80 (-20%), qty 200 (+100%). Elasticity = +100 / -20 = -5.0 (Elastic)
        "PROD_ELASTIC;Whse_North;05/01/2023;100;100;100.0;None;100.0;0.95\n"
        "PROD_ELASTIC;Whse_South;15/01/2023;100;200;100.0;Promo_Flash;80.0;0.95\n"
        # PROD_INELASTIC: Base price 50, qty 100. Promo price 40 (-20%), qty 110 (+10%). Elasticity = +10 / -20 = -0.5 (Inelastic)
        "PROD_INELASTIC;Whse_North;10/02/2023;100;100;50.0;None;50.0;0.90\n"
        "PROD_INELASTIC;Whse_South;20/02/2023;100;110;50.0;Promo_Winter;40.0;0.90\n"
        # PROD_ZERO_DELTA: Base price 60, qty 50. Promo price 60 (0%), qty 60 (+20%). Zero price variation
        "PROD_ZERO_DELTA;Whse_North;01/03/2023;50;50;60.0;None;60.0;0.99\n"
        "PROD_ZERO_DELTA;Whse_South;10/03/2023;50;60;60.0;Promo_Special;60.0;0.99\n"
        # PROD_NO_PROMO: Only non-promoted transactions (Inconclusive)
        "PROD_NO_PROMO;Whse_North;01/04/2023;80;80;30.0;None;30.0;0.92\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sales_service(elasticity_dataset):
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=elasticity_dataset)
    basic_service = BasicMetricsService()
    advanced_service = AdvancedMetricsService()
    return SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=basic_service,
        advanced_metrics_service=advanced_service,
    )


def test_integration_specific_product_elastic(sales_service):
    """Test querying a specific elastic product returns Elastic classification."""
    result = sales_service.calculate_price_elasticity(product_id="PROD_ELASTIC")
    assert isinstance(result, PriceElasticityResult)
    assert result.product_id == "PROD_ELASTIC"
    assert result.elasticity_coefficient == -5.0
    assert result.percentage_change_in_price == -20.0
    assert result.percentage_change_in_quantity == 100.0
    assert "Elastic" in result.demand_classification


def test_integration_specific_product_inelastic(sales_service):
    """Test querying a specific inelastic product returns Inelastic classification."""
    result = sales_service.calculate_price_elasticity(product_id="PROD_INELASTIC")
    assert isinstance(result, PriceElasticityResult)
    assert result.product_id == "PROD_INELASTIC"
    assert result.elasticity_coefficient == -0.5
    assert result.percentage_change_in_price == -20.0
    assert result.percentage_change_in_quantity == 10.0
    assert "Inelastic" in result.demand_classification


def test_integration_zero_price_variation(sales_service):
    """Test querying a product with zero price variation returns Unitary / Zero price change."""
    result = sales_service.calculate_price_elasticity(product_id="PROD_ZERO_DELTA")
    assert isinstance(result, PriceElasticityResult)
    assert result.product_id == "PROD_ZERO_DELTA"
    assert result.elasticity_coefficient == 0.0
    assert result.percentage_change_in_price == 0.0
    assert result.demand_classification == "Unitary / Zero price change"


def test_integration_unknown_product(sales_service):
    """Test querying an unknown product returns Undefined with explanatory summary."""
    result = sales_service.calculate_price_elasticity(product_id="PROD_UNKNOWN")
    assert isinstance(result, PriceElasticityResult)
    assert result.product_id == "PROD_UNKNOWN"
    assert result.elasticity_coefficient == 0.0
    assert result.demand_classification == "Undefined"
    assert "não encontrado" in result.summary


def test_integration_catalog_overview_ranking(sales_service):
    """Test querying without product ID returns ranked catalog overview."""
    result = sales_service.calculate_price_elasticity()
    assert isinstance(result, CatalogPriceElasticityOverview)
    assert result.total_products_evaluated == 4
    assert result.inconclusive_products_count == 1
    # Valid products: PROD_ELASTIC and PROD_INELASTIC (PROD_ZERO_DELTA is Unitary, PROD_NO_PROMO is Inconclusive)
    assert len(result.most_elastic_products) >= 2
    assert result.most_elastic_products[0].product_id == "PROD_ELASTIC"
    assert result.most_inelastic_products[0].product_id in ("PROD_ZERO_DELTA", "PROD_INELASTIC")
