"""Integration test: End-to-end domain aggregations against S3 dataset.

These tests require real S3 credentials and are skipped when credentials are unavailable.
"""
import os

import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter

_HAS_S3_CREDENTIALS = bool(
    os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
)
_S3_DATASET_PATH = os.getenv("DATASET_PATH", "s3://juliosilvacwb-private/sales.csv")


@pytest.mark.skipif(
    not _HAS_S3_CREDENTIALS or not _S3_DATASET_PATH.startswith("s3://"),
    reason="S3 credentials or S3 DATASET_PATH not available",
)
class TestS3Aggregations:
    """Validate that all domain aggregations execute correctly against an S3-backed sales_data view."""

    @pytest.fixture(autouse=True)
    def setup_adapter(self) -> None:
        """Initialize adapter with S3 URI."""
        self.adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=_S3_DATASET_PATH)

    def test_top_selling_product(self) -> None:
        """Execute aggregate_top_selling_product against S3 and verify non-null result."""
        result = self.adapter.aggregate_top_selling_product()
        assert result is not None
        assert result.product_id is not None
        assert result.total_quantity > 0

    def test_top_locations(self) -> None:
        """Execute aggregate_top_locations against S3."""
        result = self.adapter.aggregate_top_locations(limit=5)
        assert len(result) > 0
        assert result[0].local is not None

    def test_total_sales(self) -> None:
        """Execute aggregate_total_sales against S3."""
        result = self.adapter.aggregate_total_sales()
        assert result.total_records > 0
        assert result.total_revenue > 0

    def test_planned_vs_actual(self) -> None:
        """Execute aggregate_planned_vs_actual against S3."""
        result = self.adapter.aggregate_planned_vs_actual()
        assert result.total_records > 0
        assert result.total_planned_quantity > 0

    def test_promotion_impact(self) -> None:
        """Execute aggregate_promotion_impact against S3."""
        result = self.adapter.aggregate_promotion_impact()
        assert result.total_records > 0

    def test_service_level_bottlenecks(self) -> None:
        """Execute aggregate_service_level_bottlenecks against S3."""
        result = self.adapter.aggregate_service_level_bottlenecks()
        assert result.total_records > 0
        assert len(result.location_averages) > 0

    def test_revenue_deficit(self) -> None:
        """Execute aggregate_revenue_deficit against S3."""
        result = self.adapter.aggregate_revenue_deficit()
        assert result.total_records > 0

    def test_average_discount(self) -> None:
        """Execute aggregate_average_discount against S3."""
        result = self.adapter.aggregate_average_discount()
        assert result.total_records > 0

    def test_seasonality(self) -> None:
        """Execute aggregate_seasonality against S3."""
        result = self.adapter.aggregate_seasonality()
        assert result.total_records > 0
        assert len(result.monthly_volumes) > 0

    def test_price_elasticity(self) -> None:
        """Execute aggregate_price_elasticity against S3."""
        result = self.adapter.aggregate_price_elasticity()
        assert len(result) > 0

    def test_execute_read_only_query_count(self) -> None:
        """Verify execute_read_only_query returns valid count from S3 view."""
        result = self.adapter.execute_read_only_query(
            "SELECT COUNT(*) AS cnt FROM sales_data"
        )
        assert len(result) == 1
        assert result[0]["cnt"] > 0

    def test_get_sales_by_filter(self) -> None:
        """Verify get_sales_by_filter works against S3."""
        result = self.adapter.get_sales_by_filter()
        assert len(result) > 0
