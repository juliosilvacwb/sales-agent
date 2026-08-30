"""Unit tests for DuckDbSalesAdapter."""
import os
import tempfile
from datetime import date
import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.model.sale_record import SaleRecord


@pytest.fixture
def sample_csv_path():
    """Creates a temporary CSV file with sample sales data."""
    content = (
        "product_id;local;date;planned_quantity;actual_quantity;planned_price;promotion_type;actual_price;service_level\n"
        "Prod_01;Whse_A;03/01/2023;100;120;50.0;Promo10;45.0;0.95\n"
        "Prod_02;Whse_B;15/02/2023;200;180;100.0;None;100.0;0.88\n"
        "Prod_01;Whse_B;20/03/2023;150;160;50.0;;48.0;0.92\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_duckdb_sales_adapter_initialization(sample_csv_path):
    """Test DuckDbSalesAdapter initializes and loads data from CSV into memory."""
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=sample_csv_path)
    records = adapter.get_sales_by_filter()

    assert len(records) == 3
    assert isinstance(records[0], SaleRecord)
    assert records[0].product_id == "Prod_01"
    assert records[0].local == "Whse_A"
    assert records[0].date == date(2023, 1, 3)
    assert records[0].planned_quantity == 100.0
    assert records[0].actual_quantity == 120.0
    assert records[0].planned_price == 50.0
    assert records[0].actual_price == 45.0
    assert records[0].service_level == 0.95
    assert records[0].promotion_type == "Promo10"


def test_duckdb_sales_adapter_aggregations(sample_csv_path):
    """Test all native DuckDB SQL aggregation methods."""
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=sample_csv_path)

    # 1. Top selling product
    top_prod = adapter.aggregate_top_selling_product()
    assert top_prod is not None
    assert top_prod.product_id == "Prod_01"
    assert top_prod.total_quantity == 280.0
    assert top_prod.total_records == 2

    # 2. Top locations
    top_locs = adapter.aggregate_top_locations(limit=2)
    assert len(top_locs) == 2
    assert top_locs[0].local == "Whse_B"
    assert top_locs[0].total_quantity == 340.0

    # 3. Total sales
    total_sales = adapter.aggregate_total_sales()
    assert total_sales.total_quantity == 460.0
    assert total_sales.total_records == 3

    # 4. Planned vs actual
    pva = adapter.aggregate_planned_vs_actual()
    assert pva.total_planned_quantity == 450.0
    assert pva.total_actual_quantity == 460.0

    # 5. Promotion impact
    promo = adapter.aggregate_promotion_impact()
    assert promo.promoted_sales_count == 1
    assert promo.non_promoted_sales_count == 2
    assert promo.promoted_total_quantity == 120.0
    assert promo.promoted_avg_actual_price == 45.0
    assert promo.average_discount_in_promotion == 10.0

    # 6. Service level bottlenecks
    sla = adapter.aggregate_service_level_bottlenecks()
    assert sla.total_records == 3
    assert "Whse_A" in sla.location_averages
    assert "Whse_B" in sla.location_averages
    assert sla.location_averages["Whse_A"] == 0.95

    # 7. Revenue deficit
    deficit = adapter.aggregate_revenue_deficit()
    # Planned: (100*50) + (200*100) + (150*50) = 5000 + 20000 + 7500 = 32500
    # Actual: (120*45) + (180*100) + (160*48) = 5400 + 18000 + 7680 = 31080
    assert deficit.total_planned_revenue == 32500.0
    assert deficit.total_actual_revenue == 31080.0

    # 8. Average discount
    disc = adapter.aggregate_average_discount()
    assert disc.total_planned_revenue == 32500.0
    assert disc.total_actual_revenue == 31080.0
    assert "Promo10" in disc.discount_by_promotion

    # 9. Seasonality
    seas = adapter.aggregate_seasonality()
    assert "2023-01" in seas.monthly_volumes
    assert "2023-02" in seas.monthly_volumes
    assert "2023-03" in seas.monthly_volumes

    # 10. Price elasticity
    elas = adapter.aggregate_price_elasticity()
    assert elas.total_records == 3


def test_duckdb_sales_adapter_get_sales_by_filter(sample_csv_path):
    """Test filtering by product_id, local, and date ranges."""
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=sample_csv_path)

    # Filter by product_id
    prod1_records = adapter.get_sales_by_filter(product_id="Prod_01")
    assert len(prod1_records) == 2
    assert all(r.product_id == "Prod_01" for r in prod1_records)

    # Filter by local
    whse_b_records = adapter.get_sales_by_filter(local="Whse_B")
    assert len(whse_b_records) == 2
    assert all(r.local == "Whse_B" for r in whse_b_records)

    # Filter by date range
    date_filtered = adapter.get_sales_by_filter(
        start_date=date(2023, 2, 1), end_date=date(2023, 3, 31)
    )
    assert len(date_filtered) == 2
    assert {r.product_id for r in date_filtered} == {"Prod_01", "Prod_02"}


def test_duckdb_sales_adapter_execute_read_only_query(sample_csv_path):
    """Test executing raw SQL aggregate query on sales_data table."""
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=sample_csv_path)
    query = "SELECT local, SUM(actual_quantity) AS total_qty FROM sales_data GROUP BY local ORDER BY local"
    result = adapter.execute_read_only_query(query)

    assert len(result) == 2
    assert result[0] == {"local": "Whse_A", "total_qty": 120.0}
    assert result[1] == {"local": "Whse_B", "total_qty": 340.0}


def test_duckdb_sales_adapter_missing_csv():
    """Test that adapter handles missing CSV gracefully without crashing on init."""
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path="non_existent_file.csv")
    top_prod = adapter.aggregate_top_selling_product()
    assert top_prod is None
    records = adapter.get_sales_by_filter()
    assert records == []


def test_duckdb_sales_adapter_map_row_brazilian_date_string():
    """Test mapping row with Brazilian format date string."""
    row = ("Prod_01", "Whse_A", "25/12/2023", 100.0, 100.0, 50.0, 50.0, 0.95, "None")
    record = DuckDbSalesAdapter._map_row_to_entity(row)
    assert record.date == date(2023, 12, 25)


def test_duckdb_sales_adapter_external_access_disabled(sample_csv_path):
    """Test that external access functions like read_csv are blocked on raw query execution."""
    adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=sample_csv_path)
    with pytest.raises(Exception):
        adapter.execute_read_only_query(f"SELECT * FROM read_csv_auto('{sample_csv_path}')")
