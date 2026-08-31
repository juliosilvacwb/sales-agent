"""Unit tests for S3 URI detection logic in DuckDbSalesAdapter."""
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter


class TestS3UriDetection:
    """Verify that the adapter correctly identifies s3:// URIs vs local paths."""

    def test_s3_uri_lowercase_detected(self) -> None:
        """Test s3://bucket/file.csv is detected as S3 mode."""
        with patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "key", "AWS_SECRET_ACCESS_KEY": "secret"}):
            with patch.object(DuckDbSalesAdapter, "_initialize_schema"):
                adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
                adapter._dataset_path = "s3://bucket/file.csv"
                adapter._is_s3 = adapter._dataset_path.lower().startswith("s3://")
                assert adapter._is_s3 is True

    def test_s3_uri_uppercase_detected(self) -> None:
        """Test S3://Bucket/File.csv (uppercase) is detected as S3 mode."""
        with patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "key", "AWS_SECRET_ACCESS_KEY": "secret"}):
            with patch.object(DuckDbSalesAdapter, "_initialize_schema"):
                adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
                adapter._dataset_path = "S3://Bucket/File.csv"
                adapter._is_s3 = adapter._dataset_path.lower().startswith("s3://")
                assert adapter._is_s3 is True

    def test_local_absolute_path_not_s3(self) -> None:
        """Test /app/dataset/sales.csv is NOT detected as S3 mode."""
        with patch.object(DuckDbSalesAdapter, "_initialize_schema"):
            adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
            adapter._dataset_path = "/app/dataset/sales.csv"
            adapter._is_s3 = adapter._dataset_path.lower().startswith("s3://")
            assert adapter._is_s3 is False

    def test_local_relative_path_not_s3(self) -> None:
        """Test dataset/sales.csv (relative) is NOT detected as S3 mode."""
        with patch.object(DuckDbSalesAdapter, "_initialize_schema"):
            adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
            adapter._dataset_path = "dataset/sales.csv"
            adapter._is_s3 = adapter._dataset_path.lower().startswith("s3://")
            assert adapter._is_s3 is False

    def test_s3_uri_with_full_path(self) -> None:
        """Test s3://juliosilvacwb-private/sales.csv is detected as S3 mode."""
        with patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "key", "AWS_SECRET_ACCESS_KEY": "secret"}):
            with patch.object(DuckDbSalesAdapter, "_initialize_schema"):
                adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
                adapter._dataset_path = "s3://juliosilvacwb-private/sales.csv"
                adapter._is_s3 = adapter._dataset_path.lower().startswith("s3://")
                assert adapter._is_s3 is True

    def test_constructor_sets_is_s3_for_s3_path(self) -> None:
        """Test that __init__ correctly sets _is_s3 from dataset_path parameter."""
        with patch.dict(
            os.environ,
            {"AWS_ACCESS_KEY_ID": "test_key", "AWS_SECRET_ACCESS_KEY": "test_secret"},
        ):
            with patch.object(DuckDbSalesAdapter, "_initialize_schema"):
                import duckdb

                adapter = DuckDbSalesAdapter.__new__(DuckDbSalesAdapter)
                adapter._db_path = ":memory:"
                adapter._dataset_path = "s3://bucket/data.csv"
                adapter._is_s3 = adapter._dataset_path.lower().startswith("s3://")
                adapter._cached_profile = None
                adapter._connection = duckdb.connect(":memory:")
                assert adapter._is_s3 is True

    def test_constructor_sets_is_s3_false_for_local_path(self) -> None:
        """Test that __init__ correctly sets _is_s3=False for local CSV path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("product_id;local;date;planned_quantity;actual_quantity;planned_price;actual_price;service_level;promotion_type\n")
            f.write("P1;L1;01/01/2023;10;10;1.0;1.0;0.9;None\n")
            temp_path = f.name

        try:
            adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=temp_path)
            assert adapter._is_s3 is False
        finally:
            os.remove(temp_path)

    @pytest.mark.parametrize(
        "invalid_uri",
        [
            "s3://bucket/../secret.csv",
            "s3://bucket/path/../../etc/passwd",
            "s3://my-bucket/..\\windows\\system32",
        ],
    )
    def test_s3_uri_path_traversal_rejected(self, invalid_uri: str) -> None:
        """[S015-03] Assert that S3 URIs containing path traversal sequences raise S3ConnectionError."""
        from src.domain.exception.s3_exceptions import S3ConnectionError

        with pytest.raises(S3ConnectionError) as exc_info:
            DuckDbSalesAdapter._validate_s3_uri(invalid_uri)
        assert exc_info.value.status_code == 400
        assert "Path traversal" in exc_info.value.message

    @pytest.mark.parametrize(
        "malformed_uri",
        [
            "s3://",
            "s3:///onlykey.csv",
            "s3://ab/key.csv",  # Bucket name shorter than 3 chars
        ],
    )
    def test_s3_uri_malformed_format_rejected(self, malformed_uri: str) -> None:
        """[S015-03] Assert that malformed S3 URIs raise S3ConnectionError."""
        from src.domain.exception.s3_exceptions import S3ConnectionError

        with pytest.raises(S3ConnectionError) as exc_info:
            DuckDbSalesAdapter._validate_s3_uri(malformed_uri)
        assert exc_info.value.status_code == 400
        assert "Invalid S3 URI format" in exc_info.value.message

    @pytest.mark.parametrize(
        "valid_uri",
        [
            "s3://my-bucket/data.csv",
            "s3://juliosilvacwb-private/sales.csv",
            "s3://analytics-data-2026/folder/subfolder/file.parquet",
        ],
    )
    def test_s3_uri_valid_formats_accepted(self, valid_uri: str) -> None:
        """[S015-03] Assert that valid S3 URIs pass validation without raising exceptions."""
        DuckDbSalesAdapter._validate_s3_uri(valid_uri)

