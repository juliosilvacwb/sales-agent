import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


def test_service_level_bottlenecks_equal_sla_reproduction():
    """
    Automated Reproduction Test for SLA Bottlenecks when service levels are identical.
    Validates that when all locations present equal service levels (98.00%),
    the metric does not arbitrarily highlight one warehouse as a bottleneck.
    """
    adapter = DuckDbSalesAdapter(dataset_path="dataset/sales.csv")
    service = SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=BasicMetricsService(),
        advanced_metrics_service=AdvancedMetricsService(),
    )

    result = service.analyze_service_level_bottlenecks()

    # In dataset/sales.csv, all warehouses have an average SLA of 98.00%.
    # Currently, result.worst_location returns 'Whse_A' and summary claims Whse_A is a bottleneck.
    # Expected behavior when all SLAs are equal:
    # 1. worst_location should return "N/A" or "None" (or indicate no bottleneck).
    # 2. summary should state that all locations operate at equal service levels with no bottleneck.
    assert result.worst_location in ("N/A", "None", "TIE", "Nenhum"), (
        f"Expected no specific location as bottleneck when all SLAs are equal, got '{result.worst_location}'"
    )
    assert "critical sla bottleneck" not in result.summary.lower(), (
        f"Summary incorrectly reports a critical bottleneck: '{result.summary}'"
    )
