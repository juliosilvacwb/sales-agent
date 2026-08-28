"""Integration reproduction test for Incident B002 - Data Analysis Promotions."""
import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.service.sales_metrics_service import (
    SalesMetricsApplicationService,
)
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService


def test_data_analysis_promotions_reproduction():
    """Automated Reproduction Test for the Data Analysis Promotions Error.

    Validates that the total discount value and overall discount percentage are
    calculated correctly instead of returning 0.0.
    """
    adapter = DuckDbSalesAdapter(dataset_path="dataset/sales.csv")
    service = SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=BasicMetricsService(),
        advanced_metrics_service=AdvancedMetricsService(),
    )

    result = service.calculate_average_discount()

    assert result.total_discount_value > 0.0, (
        f"Expected positive discount value, got {result.total_discount_value}"
    )
    assert result.overall_average_discount_percentage > 0.0, (
        f"Expected positive discount percentage, got {result.overall_average_discount_percentage}"
    )
