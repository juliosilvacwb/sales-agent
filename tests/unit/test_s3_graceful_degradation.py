"""Unit tests for graceful degradation on S3 errors during VIEW creation."""
import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import (
    DuckDbSalesAdapter,
    _CANONICAL_SCHEMA_DDL,
)


class TestS3GracefulDegradation:
    """Verify that S3 403/404 errors during VIEW creation result in graceful fallback."""

    def _build_adapter_with_view_failure(
        self, error_msg: str = "HTTP Error 403 Forbidden"
    ) -> tuple[DuckDbSalesAdapter, MagicMock]:
        """Helper: builds an adapter where VIEW creation fails, triggering empty schema fallback."""
        env = {
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_REGION": "us-east-1",
        }
        mock_conn = MagicMock()

        call_count = [0]

        def execute_side_effect(sql: str, *args: object, **kwargs: object) -> MagicMock:
            call_count[0] += 1
            if "CREATE VIEW" in sql:
                raise RuntimeError(error_msg)
            return MagicMock()

        mock_conn.execute.side_effect = execute_side_effect

        adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
        adapter._db_path = ":memory:"
        adapter._dataset_path = "s3://bucket/data.csv"
        adapter._is_s3 = True
        adapter._cached_profile = None
        adapter._connection = mock_conn

        with patch.dict(os.environ, env, clear=False):
            adapter._initialize_schema()

        return adapter, mock_conn

    def test_view_creation_failure_creates_empty_table(self) -> None:
        """Assert empty sales_data table is created with canonical schema on VIEW failure."""
        _, mock_conn = self._build_adapter_with_view_failure("HTTP Error 403 Forbidden")
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("CREATE TABLE" in s and "sales_data" in s for s in executed_sqls)

    def test_view_creation_failure_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Assert warning log is emitted with actionable message on S3 view failure."""
        with caplog.at_level(logging.WARNING):
            self._build_adapter_with_view_failure("HTTP Error 404 Not Found")

        assert any("[S3_MODE] Failed to create S3 view:" in record.message for record in caplog.records)

    def test_adapter_remains_functional_after_view_failure(self) -> None:
        """Assert adapter remains functional (does not crash) after VIEW creation failure."""
        adapter, _ = self._build_adapter_with_view_failure("Network timeout")
        assert adapter._is_s3 is True
        assert adapter._dataset_path == "s3://bucket/data.csv"

    def test_httpfs_failure_creates_empty_table(self) -> None:
        """Assert empty schema fallback when httpfs extension fails to install."""
        mock_conn = MagicMock()

        def execute_side_effect(sql: str, *args: object, **kwargs: object) -> MagicMock:
            if "INSTALL httpfs" in sql:
                raise RuntimeError("Extension installation failed")
            return MagicMock()

        mock_conn.execute.side_effect = execute_side_effect

        adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
        adapter._db_path = ":memory:"
        adapter._dataset_path = "s3://bucket/data.csv"
        adapter._is_s3 = True
        adapter._cached_profile = None
        adapter._connection = mock_conn

        adapter._initialize_s3_schema()

        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("CREATE TABLE" in s and "sales_data" in s for s in executed_sqls)

    def test_403_forbidden_error_handled_gracefully(self) -> None:
        """Simulate S3 403 Forbidden and verify graceful fallback."""
        adapter, mock_conn = self._build_adapter_with_view_failure("HTTP Error 403: Access Denied")
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("CREATE TABLE" in s for s in executed_sqls)

    def test_404_not_found_error_handled_gracefully(self) -> None:
        """Simulate S3 404 Not Found and verify graceful fallback."""
        adapter, mock_conn = self._build_adapter_with_view_failure("HTTP Error 404: Not Found")
        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("CREATE TABLE" in s for s in executed_sqls)

    def test_s3_view_path_single_quotes_properly_escaped(self) -> None:
        """[TEST015-23] Assert that S3 path with single quotes is escaped in VIEW query."""
        env = {
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_REGION": "us-east-1",
        }
        mock_conn = MagicMock()
        adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
        adapter._db_path = ":memory:"
        adapter._dataset_path = "s3://bucket/sales'2023.csv"
        adapter._is_s3 = True
        adapter._cached_profile = None
        adapter._connection = mock_conn

        with patch.dict(os.environ, env, clear=False):
            adapter._initialize_schema()

        executed_sqls = [str(c) for c in mock_conn.execute.call_args_list]
        # Should contain escaped single quote: sales''2023.csv
        assert any("sales''2023.csv" in s for s in executed_sqls)

    def test_view_creation_failure_masks_credentials_in_log(self, caplog: pytest.LogCaptureFixture) -> None:
        """[S015-02] Assert that S3 view failure warning log masks AWS signatures and credentials."""
        with caplog.at_level(logging.WARNING):
            self._build_adapter_with_view_failure(
                "HTTP Error 403 Forbidden: Signature=12345abcdef X-Amz-Security-Token=SECRET_TOKEN"
            )

        assert any("[S3_MODE] Failed to create S3 view:" in record.message for record in caplog.records)
        assert not any("12345abcdef" in record.message for record in caplog.records)
        assert not any("SECRET_TOKEN" in record.message for record in caplog.records)
        assert any("Signature=[REDACTED]" in record.message for record in caplog.records)
        assert any("X-Amz-Security-Token=[REDACTED]" in record.message for record in caplog.records)

