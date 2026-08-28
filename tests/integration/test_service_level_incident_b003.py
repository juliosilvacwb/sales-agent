import pytest
from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.service.advanced_metrics_service import AdvancedMetricsService
from src.domain.service.basic_metrics_service import BasicMetricsService
from src.application.service.sales_metrics_service import SalesMetricsApplicationService


def test_service_level_bottlenecks_equal_sla_reproduction():
    """
    Automated Integration Test for SLA Bottlenecks.
    When location averages are equal, worst_location returns 'N/A'.
    When one location has a strictly lower average, it is identified as the bottleneck.
    """
    adapter = DuckDbSalesAdapter(dataset_path="dataset/sales.csv")
    service = SalesMetricsApplicationService(
        sales_data_port=adapter,
        basic_metrics_service=BasicMetricsService(),
        advanced_metrics_service=AdvancedMetricsService(),
    )

    result = service.analyze_service_level_bottlenecks()

    min_val = min(result.location_averages.values())
    max_val = max(result.location_averages.values())

    if min_val == max_val:
        assert result.worst_location == "N/A"
        assert "No logistics SLA bottleneck identified" in result.summary
    else:
        worst = min(result.location_averages.items(), key=lambda item: item[1])[0]
        assert result.worst_location == worst
        assert f"location '{worst}'" in result.summary
