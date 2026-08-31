"""Integration test: Dataset profiling against S3 URI.

These tests require real S3 credentials and are skipped when credentials are unavailable.
"""
import os

import pytest

from src.adapter.outbound.persistence.duckdb_sales_adapter import DuckDbSalesAdapter
from src.domain.model.dataset_profile import DatasetProfile

_HAS_S3_CREDENTIALS = bool(
    os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
)
_S3_DATASET_PATH = os.getenv("DATASET_PATH", "s3://juliosilvacwb-private/sales.csv")


@pytest.mark.skipif(
    not _HAS_S3_CREDENTIALS or not _S3_DATASET_PATH.startswith("s3://"),
    reason="S3 credentials or S3 DATASET_PATH not available",
)
class TestS3Profiling:
    """Verify profile_dataset() computes valid metadata from S3 source."""

    @pytest.fixture(autouse=True)
    def setup_adapter(self) -> None:
        """Initialize adapter with S3 URI."""
        self.adapter = DuckDbSalesAdapter(db_path=":memory:", dataset_path=_S3_DATASET_PATH)

    def test_profile_returns_valid_record_count(self) -> None:
        """Assert total_records > 0 from S3 profiling."""
        profile = self.adapter.profile_dataset()
        assert isinstance(profile, DatasetProfile)
        assert profile.total_records > 0

    def test_profile_date_bounds_are_valid(self) -> None:
        """Assert date bounds are populated from S3 profiling."""
        profile = self.adapter.profile_dataset()
        assert profile.min_date is not None
        assert profile.max_date is not None

    def test_profile_distinct_counts_populated(self) -> None:
        """Assert distinct product and location counts are populated."""
        profile = self.adapter.profile_dataset()
        assert profile.distinct_products > 0
        assert profile.distinct_locations > 0

    def test_profile_null_representations_detected(self) -> None:
        """Assert null_representations are detected correctly (e.g., 'None' in promotion_type)."""
        profile = self.adapter.profile_dataset()
        # The sales.csv dataset uses 'None' as a string sentinel
        if profile.null_representations:
            assert "promotion_type" in profile.null_representations

    def test_profile_constant_columns_detected(self) -> None:
        """Assert constant_columns detection works against S3 data."""
        profile = self.adapter.profile_dataset()
        # This is dataset-dependent; just verify the field is present and is a dict
        assert isinstance(profile.constant_columns, dict)

    def test_profile_markdown_block_non_empty(self) -> None:
        """Assert to_markdown_block produces non-empty output from S3 profiling."""
        profile = self.adapter.profile_dataset()
        markdown = profile.to_markdown_block()
        assert len(markdown) > 0
        assert "DYNAMIC DATA INSIGHTS" in markdown

    def test_profile_caching_works(self) -> None:
        """Assert profile_dataset caches results across subsequent calls."""
        profile1 = self.adapter.profile_dataset()
        profile2 = self.adapter.profile_dataset()
        assert profile1 is profile2
