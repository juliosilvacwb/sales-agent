"""Unit tests for S3 domain exceptions and port interface compatibility."""
import inspect
import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.application.port.outbound.sales_data_port import SalesDataPort
from src.domain.exception.s3_exceptions import S3ConnectionError


class TestS3Exceptions:
    """[TEST015-01, TEST015-02, TEST015-03] Tests for S3ConnectionError domain exception."""

    def test_s3_connection_error_instantiation_default_status_code(self) -> None:
        """[TEST015-01] Validates S3ConnectionError default instantiation with message."""
        msg = "Failed to connect to S3 endpoint"
        exc = S3ConnectionError(message=msg)
        assert exc.message == msg
        assert exc.status_code is None
        assert str(exc) == msg

    def test_s3_connection_error_with_custom_status_code(self) -> None:
        """[TEST015-02] Validates S3ConnectionError with explicit HTTP status code."""
        msg = "Access Denied"
        status_code = 403
        exc = S3ConnectionError(message=msg, status_code=status_code)
        assert exc.message == msg
        assert exc.status_code == status_code
        assert str(exc) == msg

    def test_s3_connection_error_is_exception_subclass(self) -> None:
        """[TEST015-03] Validates S3ConnectionError inherits directly from Python Exception."""
        assert issubclass(S3ConnectionError, Exception)
        # Verify module has zero framework imports
        import src.domain.exception.s3_exceptions as s3_mod
        module_source = inspect.getsource(s3_mod)
        assert "duckdb" not in module_source
        assert "boto" not in module_source
        assert "fastapi" not in module_source


class TestSalesDataPortCompatibility:
    """[TEST015-04, TEST015-05] Tests for SalesDataPort contract and DuckDbSalesAdapter compliance."""

    def test_sales_data_port_interface_signatures_unchanged(self) -> None:
        """[TEST015-04] Validates that SalesDataPort preserves all abstract method signatures."""
        required_methods = [
            "aggregate_top_selling_product",
            "aggregate_top_locations",
            "aggregate_total_sales",
            "aggregate_planned_vs_actual",
            "aggregate_promotion_impact",
            "aggregate_service_level_bottlenecks",
            "aggregate_revenue_deficit",
            "aggregate_average_discount",
            "aggregate_seasonality",
            "aggregate_price_elasticity",
            "execute_read_only_query",
            "get_sales_by_filter",
            "profile_dataset",
        ]
        for method_name in required_methods:
            assert hasattr(SalesDataPort, method_name)
            method = getattr(SalesDataPort, method_name)
            assert getattr(method, "__isabstractmethod__", False) is True

    def test_sales_data_port_duckdb_adapter_subclass_compliance(self) -> None:
        """[TEST015-05] Validates that DuckDbSalesAdapter implements SalesDataPort."""
        assert issubclass(DuckDbSalesAdapter, SalesDataPort)
