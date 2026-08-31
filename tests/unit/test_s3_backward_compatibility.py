"""Backward compatibility regression tests confirming local CSV functionality is unbroken."""
import os
import tempfile
from datetime import date

import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.model.dataset_profile import DatasetProfile


@pytest.fixture
def regression_csv_path() -> str:
    """Creates a comprehensive temporary CSV with sample sales data for regression testing."""
    content = (
        "product_id;local;date;planned_quantity;actual_quantity;"
        "planned_price;promotion_type;actual_price;service_level\n"
        "Prod_01;Whse_A;03/01/2023;100;120;50.0;Promo10;45.0;0.95\n"
        "Prod_02;Whse_B;15/02/2023;200;180;100.0;None;100.0;0.88\n"
        "Prod_01;Whse_B;20/03/2023;150;160;50.0;;48.0;0.92\n"
        "Prod_03;Whse_A;10/04/2023;80;90;30.0;SummerSale;25.0;0.97\n"
        "Prod_02;Whse_A;25/05/2023;120;110;100.0;None;100.0;0.91\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path  # type: ignore[misc]

    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestBackwardCompatibility:
    """Ensure existing local CSV functionality is 100% preserved after S3 changes."""

    def test_local_csv_initialization(self, regression_csv_path: str) -> None:
        """Verify adapter initializes correctly from local CSV path."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        assert adapter._is_s3 is False
        records = adapter.get_sales_by_filter()
        assert len(records) == 5

    def test_aggregate_top_selling_product(self, regression_csv_path: str) -> None:
        """Regression: aggregate_top_selling_product returns correct result."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        top = adapter.aggregate_top_selling_product()
        assert top is not None
        assert top.product_id in ("Prod_01", "Prod_02")

    def test_aggregate_top_locations(self, regression_csv_path: str) -> None:
        """Regression: aggregate_top_locations returns locations sorted by volume."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        locs = adapter.aggregate_top_locations(limit=3)
        assert len(locs) == 2  # Only 2 distinct locations
        assert locs[0].total_quantity >= locs[1].total_quantity

    def test_aggregate_total_sales(self, regression_csv_path: str) -> None:
        """Regression: aggregate_total_sales returns correct totals."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        total = adapter.aggregate_total_sales()
        assert total.total_records == 5
        assert total.total_quantity > 0
        assert total.total_revenue > 0

    def test_aggregate_total_sales_with_date_filter(self, regression_csv_path: str) -> None:
        """Regression: aggregate_total_sales with date filter works correctly."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        total = adapter.aggregate_total_sales(
            start_date=date(2023, 2, 1), end_date=date(2023, 3, 31)
        )
        assert total.total_records == 2

    def test_aggregate_planned_vs_actual(self, regression_csv_path: str) -> None:
        """Regression: aggregate_planned_vs_actual returns valid data."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        pva = adapter.aggregate_planned_vs_actual()
        assert pva.total_planned_quantity > 0
        assert pva.total_actual_quantity > 0
        assert pva.total_records == 5

    def test_aggregate_promotion_impact(self, regression_csv_path: str) -> None:
        """Regression: aggregate_promotion_impact returns valid promotion analysis."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        promo = adapter.aggregate_promotion_impact()
        assert promo.total_records == 5
        assert promo.promoted_sales_count > 0
        assert promo.non_promoted_sales_count > 0

    def test_aggregate_service_level_bottlenecks(self, regression_csv_path: str) -> None:
        """Regression: aggregate_service_level_bottlenecks returns location averages."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        sla = adapter.aggregate_service_level_bottlenecks()
        assert sla.total_records == 5
        assert "Whse_A" in sla.location_averages
        assert "Whse_B" in sla.location_averages

    def test_aggregate_revenue_deficit(self, regression_csv_path: str) -> None:
        """Regression: aggregate_revenue_deficit returns planned vs actual revenues."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        deficit = adapter.aggregate_revenue_deficit()
        assert deficit.total_planned_revenue > 0
        assert deficit.total_actual_revenue > 0
        assert deficit.total_records == 5

    def test_aggregate_average_discount(self, regression_csv_path: str) -> None:
        """Regression: aggregate_average_discount returns valid discount analysis."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        disc = adapter.aggregate_average_discount()
        assert disc.total_records == 5
        assert disc.total_planned_revenue > 0

    def test_aggregate_seasonality(self, regression_csv_path: str) -> None:
        """Regression: aggregate_seasonality returns monthly volumes."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        seas = adapter.aggregate_seasonality()
        assert len(seas.monthly_volumes) > 0
        assert seas.total_records == 5

    def test_aggregate_price_elasticity(self, regression_csv_path: str) -> None:
        """Regression: aggregate_price_elasticity returns valid per-product data."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        elas = adapter.aggregate_price_elasticity()
        assert len(elas) > 0

    def test_execute_read_only_query(self, regression_csv_path: str) -> None:
        """Regression: execute_read_only_query returns correct raw SQL results."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        result = adapter.execute_read_only_query("SELECT COUNT(*) AS cnt FROM sales_data")
        assert len(result) == 1
        assert result[0]["cnt"] == 5

    def test_profile_dataset_returns_valid_profile(self, regression_csv_path: str) -> None:
        """Regression: profile_dataset returns valid DatasetProfile."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=regression_csv_path)
        profile = adapter.profile_dataset()
        assert isinstance(profile, DatasetProfile)
        assert profile.total_records == 5
        assert profile.distinct_products == 3
        assert profile.distinct_locations == 2
        assert profile.min_date is not None
        assert profile.max_date is not None

    def test_missing_csv_still_works(self) -> None:
        """Regression: missing CSV creates empty schema without crashing."""
        adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path="nonexistent.csv")
        assert adapter._is_s3 is False
        top = adapter.aggregate_top_selling_product()
        assert top is None
        records = adapter.get_sales_by_filter()
        assert records == []
